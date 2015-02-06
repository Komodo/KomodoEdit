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
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2011
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

var koFilteredTreeView = {};
(function() {

const OPEN_NODE_PREFS_NAME = "filtered-prefs-open-nodes-by-id";
var log = ko.logging.getLogger('filtered-prefs');
var prefs = Components.classes["@activestate.com/koPrefService;1"].
    getService(Components.interfaces.koIPrefService).prefs;

var _openPrefTreeNodes;

function setupOpenPrefTreeNodes() {
    if (!prefs.hasPref(OPEN_NODE_PREFS_NAME)) {
        _openPrefTreeNodes = {};
    } else {
        _openPrefTreeNodes = JSON.parse(prefs.getStringPref(OPEN_NODE_PREFS_NAME));
    }
}

function saveOpenPrefTreeNodes() {
    Components.classes["@activestate.com/koPrefService;1"].
        getService(Components.interfaces.koIPrefService).prefs.setStringPref(OPEN_NODE_PREFS_NAME,
                                JSON.stringify(_openPrefTreeNodes));
}

var treeItemsByURI = {}; // URI => array of TreeInfoItem;

function TreeInfoItem(id, isContainer, isOpen, cls, url, label, helptag, advanced, properties) {
    this.id = id;
    this._isContainer = isContainer;
    this.cls = cls;
    this.url = url;
    this.label = label;
    this.helptag = helptag;
    this.level = 0; // for nsITreeView
    this.state = isOpen ? xtk.hierarchicalTreeView.STATE_OPENED : xtk.hierarchicalTreeView.STATE_CLOSED;
    this.filteredOut = false;
    this.advanced = advanced;
    this.properties = properties || id;
}

TreeInfoItem.prototype.getChildren = function() {
    if (!(this.url in treeItemsByURI)) {
        return [];
    }
    if (prefs.getBoolean("prefs_show_advanced", false)) {
        return treeItemsByURI[this.url];
    }
    return treeItemsByURI[this.url].filter(function(row) {
        return !row.advanced;
    });
};

TreeInfoItem.prototype.hasChildren = function() {
    return this._isContainer && this.getChildren().length > 0;
};

Object.defineProperty(TreeInfoItem.prototype, "isContainer", {
    get: function() { return this._isContainer && this.hasChildren(); },
});

Object.defineProperty(TreeInfoItem.prototype, "isContainerOpen", {
    get: function() { return this.state === xtk.hierarchicalTreeView.STATE_OPENED; },
});

TreeInfoItem.prototype.toString = function() {
    var s = [];
    for (var p in this) {
        var o = this[p];
        if (typeof(o) != "function") {
            s.push(p + ": " + o);
        }
    }
    s.push("isContainer: " + this.isContainer);
    s.push("hasChildren: " + this.hasChildren());
    return "{ " + s.join(", ") + " }";
}

this.buildTree = function(root, key, isRoot = false) {
    var i, lim, currentList, rootChildren = root.childNodes, isContainer, isOpen, url, item;
    var treeitem, treerow, treecell, treechildren, properties;
    if (typeof(key) === "undefined") key = ""; // top-level
    if (!(key in treeItemsByURI)) {
        treeItemsByURI[key] = [];
    }
    currentList = treeItemsByURI[key];
    lim = rootChildren.length;
    for (var i = 0; i < lim; i++) {
        treeitem = rootChildren[i];
        treerow = treeitem.firstChild;
        treecell = treerow.firstChild;
        isContainer = treeitem.getAttribute("container") === "true";
        if (isContainer) {
            if (treeitem.id in _openPrefTreeNodes) {
                isOpen = _openPrefTreeNodes[treeitem.id];
            } else {
                isOpen = treeitem.getAttribute("open") === "true";
            }
        }
        properties = treeitem.getAttribute("properties") || "";
        if ( ! isRoot) properties += " child-row"
        url = treecell.getAttribute("url");
        item = new TreeInfoItem(treeitem.id,
                                isContainer,
                                isOpen,
                                treecell.getAttribute("class"),
                                url,
                                treecell.getAttribute("label"),
                                treecell.getAttribute("helptag"),
                                treeitem.getAttribute("advanced") == "true",
                                properties);
        currentList.push(item);
        if (isContainer) {
            if (treeitem.childNodes.length != 2) {
                throw new Error("container for url " + url + " has " + treeitem.childNodes.length + " nodes");
            }
            treechildren = treeitem.lastChild;
            if (treechildren.nodeName != "treechildren") {
                throw new Error("expected a treechildren node for url " + url + ", got " + treechildren.nodeName);
            }
            this.buildTree(treechildren, url);
        } else if (treeitem.childNodes.length != 1) {
            throw new Error("non-container has " + treeitem.childNodes.length + " nodes");
        }
    }
};

this.getPrefTreeView = function() {
    setupOpenPrefTreeNodes();
    var rows = treeItemsByURI[""];
    if (!rows || rows.length == 0) {
        this.buildTree(document.getElementById("panelChildren"), "", true);
        rows = treeItemsByURI[""];
        if (!rows || rows.length == 0) {
            throw new Error("No rows for PrefTreeView");
        }
    }
    this.prefTreeView = new PrefTreeView(rows);
    return this.prefTreeView;
};

function PrefTreeView(initial_rows) {
    xtk.hierarchicalTreeView.apply(this, [initial_rows]);
    this._atomService = Components.classes["@mozilla.org/atom-service;1"].
                            getService(Components.interfaces.nsIAtomService);
    this.enableSorting = false;
    this.filtering = false;
    // Three kinds of rows in this tree:
    // this._rows -- the current view of rows, which the parent class expects to work with
    //               it can be a filtered view
    // this._unfilteredRows -- the rows to show when there's no filter in place
    // this._totalRows -- the full tree of rows, which filtered rows are built from.
    this._buildAllRows();
    this._processOpenContainerRows();
    this._unfilteredRows = this._rows;
};
PrefTreeView.prototype = new xtk.hierarchicalTreeView();
PrefTreeView.prototype.constructor = PrefTreeView;
// and other nsITreeView methods
PrefTreeView.prototype.getCellText = function(row, column) {
    return this._rows[row].label;
};
PrefTreeView.prototype.getRowProperties = function(row, column) {
    return this._rows[row].properties;
};
PrefTreeView.prototype.getCellProperties = function(row, column) {
    return this._rows[row].properties;
};
PrefTreeView.prototype.getCellValue = function(row, column) {
    if (typeof(row) == "undefined"
        || typeof(this._rows[row]) == "undefined"
        || typeof([column.id]) == "undefined"
        || typeof(this._rows[row][column.id]) == "undefined") {
    }
    return this._rows[row][column.id];
};
PrefTreeView.prototype.isContainerEmpty = function(row) {
    return false; // no empty containers in this tree
};
PrefTreeView.prototype.isContainer = function(row) { 
    return this._rows[row].isContainer;
};
PrefTreeView.prototype.isContainerOpen = function(row) {
    return this._rows[row].isContainerOpen;
};

PrefTreeView.prototype._buildAllRows = function() {
    var totalRows = [];
    var i, row, lim = this._rows.length;
    for (i = 0; i < lim; i ++) {
        row = this._rows[i];
        totalRows.push(row);
        if (row.isContainer) {
            var newRows = this._extendChildren(row, totalRows);
        }
    }
    this._totalRows = totalRows;
};

PrefTreeView.prototype._extendChildren = function(rowItem, totalRows) {
    var rows = [];
    var child;
    var state;
    var children = rowItem.getChildren();
    var child_level = rowItem.level + 1;
    for (var i = 0; i < children.length; i++) {
        child = children[i];
        child.level = child_level;
        totalRows.push(child);
        if (child.isContainer) {
            rows = rows.concat(this._extendChildren(child, totalRows));
        }
    }
    
};

PrefTreeView.prototype.toggleOpenState = function(row, updateTree) {
    if (this.filtering) {
        // don't bother updating toggles while we're filtering
        return;
    }
    var item = this._rows[row];
    if (!item.isContainer) {
        return;
    }
    if (typeof(updateTree) == "undefined") updateTree = true;
    var new_rows;

    if (!item.isContainerOpen) {
        var children = [];
        this._expand_child_rows(item, children);
        new_rows = this._rows.slice(0, row+1);
        new_rows = new_rows.concat(children);
        new_rows = new_rows.concat(this._rows.slice(row+1));
        item.state = xtk.hierarchicalTreeView.STATE_OPENED;
    } else {
        var level = this._rows[row].level;
        var r = row + 1;
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
    if (updateTree) {
        _openPrefTreeNodes[item.id] = item.isContainerOpen;
        this.tree.rowCountChanged(row+1, num_rows_changed);
        this.tree.invalidateRow(row); // To redraw the twisty.
    }
};

PrefTreeView.prototype.doApply = function() {
    saveOpenPrefTreeNodes();
};

PrefTreeView.prototype._processOpenContainerRows = function() {
    var i, row, lim = this._rows.length;
    for (var i = lim - 1; i >= 0; i--) {
        row = this._rows[i];
        if (row.isContainer && row.isContainerOpen) {
            // get toggleOpenState to do all the work
            row.state = xtk.hierarchicalTreeView.STATE_CLOSED;
            this.toggleOpenState(i, /*updateTree=*/ false);
        }
    }
};

PrefTreeView.prototype._expand_child_rows = function(rowItem, newChildren) {
    var child_level = rowItem.level + 1;
    var this_ = this;
    rowItem.getChildren().forEach(function(child) {
        child.level = child_level;
        newChildren.push(child);
        if (child.isContainer && child.isContainerOpen) {
            this_._expand_child_rows(child, newChildren);
        }
    })
};

PrefTreeView.prototype._applyFilter = function(status) {
    this._rows.forEach(function(row) { row.filteredOut = status; });
}
PrefTreeView.prototype.removeFilter = function() {
    this.filtering = false;
    this._applyFilter(false);
    var oldCount = this._rows.length;
    var showAdvanced = prefs.getBoolean("prefs_show_advanced", false);
    this._rows = this._unfilteredRows.filter(function(row) {
        return showAdvanced || ! row.advanced;
    });
    this.tree.rowCountChanged(oldCount, this._rows.length - oldCount);
    this.tree.invalidate();
};
PrefTreeView.prototype.filterEverything = function() {
    this.filtering = true;
    this._applyFilter(true);
    var oldCount = this._rows.length;
    this._rows = [];
    this.tree.rowCountChanged(0, -oldCount);
    this.tree.invalidate();
};
PrefTreeView.prototype.updateFilter = function(urls) {
    var i, j, i1, row;
    var originalRows = this._rows;
    var oldCount = this._rows.length;
    var showAdvanced = prefs.getBoolean("prefs_show_advanced", false);
    // assign the total rows to this._rows so getParentIndex can work
    this._rows = this._totalRows;
    this._rows.forEach(function(rowItem) {
        rowItem.filteredOut = true;
        if (rowItem.isContainer) {
            rowItem.state = xtk.hierarchicalTreeView.STATE_CLOSED;
        }
    });
    var lim = this._rows.length;
    for (i = lim - 1; i >= 0; i--) {
        row = this._rows[i];
        if (row.filteredOut && urls.indexOf(row.url) != -1 && (showAdvanced || !row.advanced)) {
            row.filteredOut = false;
            i1 = i;
            while ((j = this.getParentIndex(i1)) != -1) {
                this._rows[j].filteredOut = false;
                this._rows[j].state = xtk.hierarchicalTreeView.STATE_OPENED;
                i1 = j;
            }
        }
    }
    this.filtering = true;
    var newFilteredRows = this._rows.filter(function(row) !row.filteredOut);
    this._rows = newFilteredRows;
    this.tree.rowCountChanged(0, newFilteredRows.length - oldCount);
    this.tree.invalidate();
};
PrefTreeView.prototype.getIndexById = function(id) {
    for (var i = this._rows.length - 1; i >= 0; i--) {
        if (this._rows[i].id === id) {
            return i;
        }
    }
    return -1;
};

/** findChild
 * Look at the children of closed items to find a buried pref item.
 * Open the tree around each node in the path to the target row,
 * and return the new index.
 */
PrefTreeView.prototype.findChild = function(id) {
    var row, nodePath;
    for (var i = this._rows.length - 1; i >= 0; i--) {
        row = this._rows[i];
        if (row.isContainer && !row.isContainerOpen) {
            nodePath = [];
            if (this._burrowForChildren(id, row, nodePath)) {
                nodePath.unshift([row, i]);
                this._openNodes(nodePath);
                // Return the location of the exposed node
                return this.getIndexById(id);
            }
        }
    }
    return -1;
};

PrefTreeView.prototype._openNodes = function(nodePath) {
    var i, lim, row, idx, prevIdx = 0;
    while (nodePath.length > 0) {
        [row, idx] = nodePath.shift();
        if (row.isContainer && !row.isContainerOpen) {
            if (row == this._rows[idx]) {
                this.toggleOpenState(idx);
                prevIdx = idx;
            } else {
                lim = this._rows.length;
                prevIdx = -1;
                for (i = prevIdx; i < lim; i++) {
                    if (this._rows[i].id == row.id) {
                        this.toggleOpenState(i);
                        prevIdx = i;
                    }
                }
                if (prevIdx == -1) {
                    break;
                }
            }
        } else {
            prevIdx = idx;
        }
    }
}

PrefTreeView.prototype._burrowForChildren = function(id, rowItem, nodePath) {
    var i, row, children = rowItem.getChildren();
    if (!children) {
        return false;
    }
    var lim = children.length;
    for (i = 0; i < lim; i++) {
        row = children[i];
        if (row.id == id) {
            nodePath.push([row, i]);
            return true;
        }
    }
    for (i = 0; i < lim; i++) {
        row = children[i];
        if (row.isContainer && this._burrowForChildren(id, row, nodePath)) {
            nodePath.unshift([row, i]);
            return true;
        }
    }
    return false;
};

PrefTreeView.prototype.getCurrentSelectedId = function() {
    var selectedRowIdx = this.selection.currentIndex;
    return selectedRowIdx === -1 ? null : this._rows[selectedRowIdx].id;
};
PrefTreeView.prototype.tryToSelectPanelId = function(selectedId) {
    if (selectedId === null) {
        return;
    }
    var newRows = this._rows;
    var i;
    if (newRows.length > 0) {
        if (selectedId !== null) {
            for (i = 0; i < newRows.length; i++) {
                if (newRows[i].id === selectedId) {
                    break;
                }
            }
            if (i < newRows.length) {
                this.selection.select(i); // currentIndex = i;
            } else {
                this.selection.select(0);
                i = 0;
            }
            this.tree.ensureRowIsVisible(i);
            this.tree.invalidateRow(i);
        }
    } else {
        // No need to do anything
    }
};

this.PrefTreeView = PrefTreeView;

this.findBounds = function(target) {
    // find the lowest i s.t. wordList[i] >= target
    if (!target) return -1;
    var lb = 0, hb = this.wordList.length - 1, mid;
    while (lb <= hb) {
        mid = Math.floor((lb + hb) / 2);
        var currentWord = this.wordList[mid];
        if (currentWord < target) {
            lb = mid + 1;
        } else if (currentWord == target) {
            return mid;
        } else if (mid == lb || this.wordList[mid - 1] < target) {
            // currentWord > target for rest
            return mid;
        } else {
            hb = mid - 1;
        }
    }
    return -1;
}

this.getHitsForWord = function(target) {
    var hit = this.findBounds(target);
    var hits = {};
    if (hit == -1) {
        this.prefTreeView.filterEverything();
        return hits;
    }
    var word, lim = this.wordList.length;
    for (var i = hit; i < lim; i++) {
        word = this.wordList[i];
        if (word.indexOf(target) != 0) {
            break;
        }
        for each (var num in this.fullTextManager.numsFromWord(word)) {
            hits[num] = 1;
        }
    }
    return hits;
};

this._intersectSets = function(set1, set2) {
    var iset = {};
    for (var p in set1) {
        if (p in set2) {
            iset[p] = set1[p];
        }
    }
    return iset;
};
this.updateFilter = function(target) {
    var selectedId = this.prefTreeView.getCurrentSelectedId();
    try {
        if (!target) {
            this.prefTreeView.removeFilter();
            return;
        }
        if (target == "-1") {
            target = "";
        }
        // Support multi-word queries by splitting target on spaces
        // Interpret w1 w2 w3 ... wn into groups, where each run of
        // words w[i] w[i+1] ... w[j] is a run if its intersection is non-empty.
        // Then take the union of all runs.
        var targets = target.replace(/^\s+/, "").replace(/\s+$/,"").
            toLowerCase().split(/\s+/);
        if (!targets.length || !targets[0]) {
            this.prefTreeView.removeFilter();
            return;
        }
        var lim = targets.length;
        var i;
        var currentSet = this.getHitsForWord(targets[0]);
        for (i = 1; i < lim; i++) {
            currentSet = this._intersectSets(currentSet,
                                             this.getHitsForWord(targets[i]));
        }
        var urls = [];
        for (var num in currentSet) {
            urls.push(this.urlManager.URLsFromNums(num));
        }
        this.prefTreeView.updateFilter(urls);
    } finally {
        this.prefTreeView.tryToSelectPanelId(selectedId);
    }
};

function URLManager() {
    this._urlToNumber = {};
    this._numberToURL = {};
    this._docNumber = 0;
}
URLManager.prototype = {
    intern: function(url) {
        if (url in this._urlToNumber) {
            return this._urlToNumber[url];
        }
        this._docNumber += 1;
        this._urlToNumber[url] = this._docNumber;
        this._numberToURL[this._docNumber] = url;
        return this._docNumber;
    },
    URLsFromNums: function(num) {
        return this._numberToURL[num];
    },
    __EOF__:null
};

function FullTextManager() {
    this._hits_for_word = {};
    this._hits_list = {};
};
FullTextManager.prototype = {
    record: function(word, urlNum) {
        if (word) {
            if (!(word in this._hits_for_word)) {
                this._hits_for_word[word] = {};
            }
            this._hits_for_word[word][urlNum] = 1;
        }
    },
    getWordList: function() {
        var wordList = Object.keys(this._hits_for_word);
        wordList.sort();
        return wordList;
    },
    
    numsFromWord: function(word) {
        if (!(word in this._hits_for_word)) {
            return [];
        } else if (word in this._hits_list) {
            return this._hits_list[word];
        } else {
            var nums = Object.keys(this._hits_for_word[word]);
            nums.sort();
            this._hits_list[word] = nums;
            return nums;
        }
    },
    __EOF__:null
};

this.loadPrefsFullText = function() {
    var tree = document.getElementById("prefsTree");
    var elts = tree.getElementsByTagName("treecell");
    var lim = elts.length;
    var urls = []
    var i, elt, url;
    for (i = 0; elt = elts[i]; i++) {
        if (!!(url = elt.getAttribute("url"))) {
            urls.push(url);
        }
    }
    const XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";
    var this_ = this;
    this.urlManager = new URLManager();
    this.fullTextManager = new FullTextManager();
    
    var DocLoader = function() {
        this.urlIndex = 0;
        this.urlCount = urls.length;
        this.overlays = {}; // hash of overlay URLs to an array of urls
        this.overlayURLs = [];
        this.beforeOverlays = true;
    };
    DocLoader.prototype.doNextURL = function() {
        if (this.urlIndex >= this.urlCount) {
            if (this.beforeOverlays) {
                this.beforeOverlays = false;
                this.urlIndex = 0;
                this.urlCount = this.overlayURLs.length;
                urls = this.overlayURLs;
            } else {
                this.getTopLevelWords();
                this_.wordList = this_.fullTextManager.getWordList();
                //document.getElementById("pref-filter-textbox").removeAttribute("readonly");
                return;
            }
        }
        var url = urls[this.urlIndex];
        
        var req = new XMLHttpRequest();
        var docLoader = this;
        req.onreadystatechange = function() {
            if (req.readyState == 4 && (req.status == 200 || req.status == 0)) { // 0? it happens...
                docLoader.onDocLoaded(req.responseXML);
            }
        };
        req.open("GET", url, true);
        req.overrideMimeType('text/xml; charset=utf-8');
        req.send(null);
    };
    DocLoader.prototype.onDocLoaded = function(docObject) {
        var i, len, cd1, node;
        var url = urls[this.urlIndex];

        var phrases = [];
        var xpr = docObject.getElementsByTagNameNS(XUL_NS, "description");
        len = xpr.length;
        for (var i = 0; i < len; i++) {
            phrases.push(xpr[i].textContent.toLowerCase());
        }
        xpr = docObject.getElementsByTagNameNS(XUL_NS, "label");
        len = xpr.length;
        for (var i = 0; i < len; i++) {
            phrases.push(xpr[i].getAttribute("value").toLowerCase());
        }
        var attrNames = {"label":true, "tooltiptext":true};
        for (var attrName in attrNames) {
            xpr = docObject.evaluate("//*/@" + attrName, docObject, null,XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null );
            for (var i = 0; i < xpr.snapshotLength; i++) {
                try {
                    phrases.push(xpr.snapshotItem(i).value.toLowerCase());
                }  catch(ex) {
                    log.error("Problem getting attr " + attrName + ":" + ex);
                }
            }
        }
        // Watch out for overlays
        if (this.beforeOverlays) {
            // No, we don't bother with nested overlays....
            len = docObject.childNodes.length;
            const PINode = docObject.childNodes[0].PROCESSING_INSTRUCTION_NODE;
            for (var i = 0; i < len && !!(node = docObject.childNodes[i]); i++) {
                if (node.nodeType == PINode && node.nodeName == "xul-overlay") {
                    var data = node.data;
                    var m = /href="(.*?)"/.exec(node.data);
                    if (m && m[1]) {
                        var overlayURI = m[1];
                        if (!(overlayURI in this.overlays)) {
                            this.overlays[overlayURI] = [];
                            this.overlayURLs.push(overlayURI);
                        }
                        this.overlays[overlayURI].push(url);
                    }
                }
            }
        }
        if (phrases.length) {
            var words = this.getWordPrefixes(phrases.join(" "));
            if (this.beforeOverlays) {
                this.internWords(url, words, this_);
            } else {
                var targetURLs = this.overlays[url];
                var i, lim = targetURLs.length;
                for (i = 0; i < lim; i++) {
                    this.internWords(targetURLs[i], words, this_);
                }
            }
        }
        this.urlIndex += 1;
        this.doNextURL();
    };
    DocLoader.prototype.getTopLevelWords = function(docObject) {
        var nodes = document.getElementsByTagName("treecell");
        var lim = nodes.length;
        var i, node, label, url, words;
        var phrases = [];
        for (var i = 0; i < lim && (node = nodes[i]); i++) {
            label = node.getAttribute("label").toLowerCase(); 
            url = node.getAttribute("url");
            if (label && url) {
                words = this.getWordPrefixes(label);
                this.internWords(url, words, this_);
            }
        }
    };
    DocLoader.prototype.getWordPrefixes = function(s) {
        // Handles latin1 characters only
        const words = (s.replace(/([a-zA-Z\xa0-\xff])[^a-zA-Z\xa0-\xff_\-\'\s]+/g, "$1").
                     replace(/[^a-zA-Z\xa0-\xff\'\-\_]+/g, " ").
                     replace(/'([a-zA-Z\xa0-\xff\-]*)'/, "$1").
                     split(/\s+/));
        const nonAlpha = /[\-_\s]+/;
        // build a flattened list of all terms in 'words' that can be
        // split into multiple sub-words.
        const subWords = words.filter(function(w) nonAlpha.test(w))
                        .reduce(function(prevWords, w) prevWords.concat(w.split(nonAlpha)),
                                []);
        return words.concat(subWords);
    };
    DocLoader.prototype.internWords = function(url, words, owner) {
        var urlNum = owner.urlManager.intern(url);
        words.forEach(function(word) {
            owner.fullTextManager.record(word, urlNum);
        });
    };

    (new DocLoader()).doNextURL();
};

}).apply(koFilteredTreeView);
