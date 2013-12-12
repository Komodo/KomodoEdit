/*
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Initial Developer of the Original Code is
# Davide Ficano.
# Portions created by the Initial Developer are Copyright (C) 2007
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Davide Ficano <davide.ficano@gmail.com>
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
*/

function KlintInfo(filterType) {
    // use setter
    this.filterType = filterType;
    this._currentSortColumnName = "klint-linenum";
    this._sortInfo = {};
    this._filterPattern = "";

    this._sortInfo["klint-linenum"] = { isAscending: true,
            sorter : function(direction) {
                return function(a, b) {
                    return direction * (a.lineStart - b.lineStart);
                };
            }
        };
    this._sortInfo["klint-messageType"] = { isAscending: true,
            sorter : function(direction) {
                return function(a, b) {
                    if (a.severity == b.severity) {
                        return a.lineStart - b.lineStart;
                    }
                    return direction * (a.severity - b.severity);
                };
            }
        };
    this._sortInfo["klint-message"] = { isAscending: true,
            sorter : function(direction) {
                return function(a, b) {
                    var cmp = a.description.toLowerCase()
                              .localeCompare(b.description.toLowerCase());
                    if (cmp == 0) {
                        if (a.lineStart == b.lineStart) {
                            return a.severity - b.severity;
                        }
                        return a.lineStart - b.lineStart;
                    }
                    return direction * cmp;
                };
            }
        };
}

KlintInfo.prototype = {
    get filterType() {
        return this._filterType;
    },

    set filterType(value) {
        if (typeof(value) == "undefined" || value == null) {
            this._filterType = KlintTreeView.ALL;
        } else {
            this._filterType = value;
        }
    },

    get currentSortColumnName() {
        return this._currentSortColumnName;
    },

    get filterPattern() {
        return this._filterPattern;
    },

    set filterPattern(value) {
        if (typeof(value) == "undefined" || value == null) {
            this._filterPattern = "";
        } else {
            this._filterPattern = value.toLowerCase();
        }
    },

    /**
     * Return true if column has been sorted ascending, false otherwise
     */
    changeSortColumn : function(columnName) {
        if (this._currentSortColumnName == columnName) {
            if (columnName in this._sortInfo) {
                this._sortInfo[columnName].isAscending = !this._sortInfo[columnName].isAscending;
            } else {
                alert("Unable to find column '" + columnName + "'");
            }
        } else {
            this._currentSortColumnName = columnName;
        }
        return this._sortInfo[columnName].isAscending;
    },

    getCurrentSortInfo : function() {
        return this._sortInfo[this._currentSortColumnName];
    },

    isResultVisible : function(koILintResult) {
        if (koILintResult.severity & this.filterType) {
            if (this._filterPattern.length == 0) {
                return true;
            }
            var descr = koILintResult.description.toLowerCase();
            if (descr.indexOf(this._filterPattern) >= 0) {
                return true;
            }
        }
        return false;
    }
}

function KlintTreeView() {
    this._count = 0;
    this._resultsObj = null;
    this._visibleItems = [];

    this.treebox = null;
}

KlintTreeView.INFO = Components.interfaces.koILintResult.SEV_INFO;
KlintTreeView.ERROR = Components.interfaces.koILintResult.SEV_ERROR;
KlintTreeView.WARNING = Components.interfaces.koILintResult.SEV_WARNING;
KlintTreeView.ALL = KlintTreeView.INFO | KlintTreeView.ERROR | KlintTreeView.WARNING;
KlintTreeView.NONE = -1;

// Properties to style tree
KlintTreeView.props = [];
KlintTreeView.props[KlintTreeView.INFO] = "info";
KlintTreeView.props[KlintTreeView.ERROR] = "error";
KlintTreeView.props[KlintTreeView.WARNING] = "warning";
// Mozilla 21 and older uses the atom service.
KlintTreeView.atomprops = [];
KlintTreeView.atomprops[KlintTreeView.INFO] =
    Components.classes["@mozilla.org/atom-service;1"]
        .getService(Components.interfaces.nsIAtomService)
        .getAtom("info");
KlintTreeView.atomprops[KlintTreeView.ERROR] =
    Components.classes["@mozilla.org/atom-service;1"]
        .getService(Components.interfaces.nsIAtomService)
        .getAtom("error");
KlintTreeView.atomprops[KlintTreeView.WARNING] =
    Components.classes["@mozilla.org/atom-service;1"]
        .getService(Components.interfaces.nsIAtomService)
        .getAtom("warning");

// Messages
KlintTreeView.messages = [];
KlintTreeView.messages[KlintTreeView.INFO] = extensions.dafizilla.klint.commonUtils.getLocalizedMessage("info.label");
KlintTreeView.messages[KlintTreeView.ERROR] = extensions.dafizilla.klint.commonUtils.getLocalizedMessage("error.label");
KlintTreeView.messages[KlintTreeView.WARNING] = extensions.dafizilla.klint.commonUtils.getLocalizedMessage("warning.label");

KlintTreeView.prototype = {
    setResultsObj : function(resultsObj, count, info) {
        this._resultsObj = resultsObj;
        this._count = count;

        if (typeof(info) == "undefined" || info == null) {
            info = new KlintInfo();
        }
        this.filterVisibleItems(info);
    },

    filterVisibleItems : function(info, sortItems) {
        var oldLen = this._visibleItems.length;
        this._visibleItems = [];

        if (typeof sortItems == "undefined" || sortItems == null) {
            sortItems = true;
        }

        if (info.filterType != KlintTreeView.NONE) {
            for (var i = 0; i < this._count; i++) {
                var result = this._resultsObj.value[i];
                if (info.isResultVisible(result)) {
                    this._visibleItems.push(result);
                }
            }
            // sort at every new filter, very inefficient
            if (sortItems) {
                this.sort(info.getCurrentSortInfo());
            }
        }
        try {
            var newLen = this._visibleItems.length;
            if (oldLen < newLen) {
                this.treebox.rowCountChanged(oldLen, newLen - oldLen);
            } else if (oldLen > newLen) {
                this.treebox.rowCountChanged(newLen, newLen - oldLen);
            }
            this.treebox.invalidate();
        } catch(ex) {
            dump("Error invalidating: " + ex + "\n");
        }
    },

    invalidate : function() {
        this.treebox.invalidate();
    },

    sort : function (sortInfo) {
        var direction = sortInfo.isAscending ? 1 : -1;
        this._visibleItems.sort(sortInfo.sorter(direction));
    },

    removeAllItems : function() {
        this.selection.clearSelection();
    },

    refresh : function() {
        this.treebox.invalidate();
    },

    getCellText : function(row, column){
        switch (column.id || column) {
            case "klint-linenum":
                return this._visibleItems[row].lineStart;
            case "klint-message":
                return this._visibleItems[row].description;
            case "klint-messageType":
                return KlintTreeView.messages[this._visibleItems[row].severity];
        }

        return "";
    },

    get selectedItem() {
        return this._visibleItems[this.selection.currentIndex];
    },

    get rowCount() {
        return this._visibleItems.length;
    },

    cycleCell: function(row, column) {},

    getImageSrc: function (row, column) {
        return null;
    },

    setTree: function(treebox){
        this.treebox = treebox;
    },

    getCellProperties: function(row, column) {
        switch (column.id || column) {
            case "klint-message":
                var severity = this._visibleItems[row].severity;
                // Mozilla 22+ does not have a properties argument.
                return KlintTreeView.props[severity];
        }
        return "";
    },

    isContainerOpen: function(index) {},
    isContainerEmpty: function(index) {},
    canDrop: function(index, orientation, dataTransfer) {},
    drop: function(row, orientation, dataTransfer) {},
    getParentIndex: function(rowIndex) -1,
    hasNextSibling: function(rowIndex, afterIndex) {},
    getProgressMode: function(row, col) {},
    getCellValue: function(row, col) {},
    toggleOpenState: function(index) {},
    selectionChanged: function() {},
    isEditable: function(row, col) {},
    isSelectable: function(row, col) {},
    setCellValue: function(row, col, value) {},
    setCellText: function(row, col, value) {},
    performAction: function(action) {},
    performActionOnRow: function(action, row) {},
    performActionOnCell: function(action, row, col) {},
    cycleHeader: function(col, elem) {},
    isContainer: function(row){ return false; },
    isSeparator: function(row){ return false; },
    isSorted: function(row){ return false; },
    getLevel: function(row){ return 0; },
    getRowProperties: function(row,props){},
    getColumnProperties: function(colid,col,props){}
};
