/* Copyright (c) 2009 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/* Fast open functionality.
 *
 * Defines the "ko.fastopen" namespace.
 */

if (typeof(ko) == 'undefined') {
    var ko = {};
}

ko.fastopen = {};
(function() {

    var log = ko.logging.getLogger("fastopen");


    //---- public interface

    this.open_gotofile_dialog = function open_gotofile_dialog() {
        var obj = new Object();
        ko.windowManager.openDialog("chrome://fastopen/content/gotofile.xul",
            "dialog-gotofile",
            "chrome,modal,centerscreen,titlebar,resizable=yes",
            obj);
    }

    this.open_invoketool_panel = function open_invoketool_panel(pos, x, y) {
        var panel = document.getElementById("invoketool_panel");
        panel.openPopup(ko.views.manager.currentView, pos, x, y);
        panel.sizeTo(400, 400);
    }


    //---- support routines

    //this.switch_to_open_view = function switch_to_open_view(pattern) {
    //    // Find the matching views.
    //    var i, view, name, type;
    //    var views = _get_view_mgr().topView.getViews(true);
    //    var matches = [];
    //    var norm_pattern = pattern.toLowerCase();
    //    for (i = 0; i < views.length; ++i) {
    //        view = views[i];
    //        type = view.getAttribute("type")
    //        switch (type) {
    //        case "tabbed":
    //            name = null;
    //            break;
    //        case "browser":
    //        case "editor":
    //        case "diff":
    //            name = view.koDoc.displayPath;
    //            break;
    //        case "startpage":
    //            name = "Start Page";
    //            break;
    //        default:
    //            log.debug("unexpected view type: '"+type+"' (ignoring)")
    //            name = null;
    //        }
    //        if (name && name.toLowerCase().indexOf(norm_pattern) != -1) {
    //            matches.push({"name": name, "type": type, "view": view});
    //        }
    //    }
    //    
    //    // Open the matching views if any.
    //    if (matches.length == 0) {
    //        return "no open views match '"+pattern+"'";
    //    } else if (matches.length == 1) {
    //        matches[0].view.makeCurrent();
    //    } else {
    //        function pick_name(match) {
    //            return match.name;
    //        }
    //        var selection = ko.dialogs.selectFromList(
    //            "Select View to Open", //title
    //            "Multiple open views match your pattern. Select the one "
    //                +"you'd like to switch to.", // prompt
    //            matches, // items
    //            "one", // selectionCondition
    //            pick_name); // stringifier
    //        if (selection) {
    //            selection[0].view.makeCurrent();
    //        } else {
    //            return "";
    //        }
    //    }
    //    return null;
    //}

    //function _get_view_mgr() {
    //    return ko.views.manager;
    //}

}).apply(ko.fastopen);


ko.fastopen.invoketool = {};
(function() {
    this.onPopupShown = function onPopupShown() {
        if (this._treeView == null) {
            this._treeView = new ToolsTreeView();
            var resultsTree = document.getElementById("invoketool_results");
            resultsTree.treeBoxObject.view = this._treeView;
            this.findTools();
        }
        var queryTextbox = document.getElementById("invoketool_query");
        queryTextbox.focus();
        queryTextbox.select();
    }
    
    this.findTools = function findTools() {
        var query = document.getElementById("invoketool_query").value;
        var tbSvc = Components.classes["@activestate.com/koToolbox2Service;1"]
            .getService(Components.interfaces.koIToolbox2Service);
        var hits = tbSvc.findTools(query, {});
        this._treeView.setHits(hits);
        //TODO: move tree selection to first one
    }
  
    this.onPanelKeyPress = function onPanelKeyPress(event) {
        if (event.keyCode == KeyEvent.DOM_VK_ENTER
            || event.keyCode == KeyEvent.DOM_VK_RETURN) {
            if (this._isMac ? event.metaKey : event.ctrlKey) {
                this.editPropertiesCurrSelection();
            } else {
                this.invokeCurrSelection();
            }
            event.stopPropagation();
            event.preventDefault();
        }

        // What we really want is to close the panel for any keypress that
        // will pass through and do something in the Komodo window, e.g.
        // Ctrl+W (Cmd+W) to close the current tab. However, I don't know
        // how to segment that... leaving the only solution to hard code
        // those keybindings we know *should* be preceded by closing this
        // panel. **Note: Haven't bothered doing that yet.**
        // Problem keybindings:
        // - Ctrl+W (Cmd+W)
        // - Shift+(Up|Down) when focus in the tree
    }

    this.onQueryKeyPress = function onQueryKeyPress(event) {
        var index;
        var keyCode = event.keyCode;
        var resultsTree = document.getElementById("invoketool_results");
        if (keyCode == KeyEvent.DOM_VK_ENTER
            || keyCode == KeyEvent.DOM_VK_RETURN)
        {
            if (this._isMac ? event.metaKey : event.ctrlKey) {
                this.editPropertiesCurrSelection();
            } else {
                this.invokeCurrSelection();
            }
            event.stopPropagation();
            event.preventDefault();
        } else if (keyCode == KeyEvent.DOM_VK_UP && event.shiftKey) {
            index = resultsTree.currentIndex - 1;
            if (index >= 0) {
                _extendSelectTreeRow(resultsTree, index);
            }
            event.preventDefault();
            event.stopPropagation();
        } else if (keyCode == KeyEvent.DOM_VK_DOWN && event.shiftKey) {
            index = resultsTree.currentIndex + 1;
            if (index < 0) {
                index = 0;
            }
            if (index < resultsTree.view.rowCount) {
                _extendSelectTreeRow(resultsTree, index);
            }
            event.preventDefault();
            event.stopPropagation();
        } else if (keyCode == KeyEvent.DOM_VK_UP
                || (keyCode == KeyEvent.DOM_VK_TAB && event.shiftKey)
                /* Ctrl+p for Emacs-y people. */
                || (event.ctrlKey && event.charCode === 112)) {
            index = resultsTree.currentIndex - 1;
            if (index >= 0) {
                _selectTreeRow(resultsTree, index);
            }
            event.preventDefault();
            event.stopPropagation();
        } else if (keyCode == KeyEvent.DOM_VK_DOWN
                || keyCode == KeyEvent.DOM_VK_TAB
                /* Ctrl+n for Emacs-y people. */
                || (event.ctrlKey && event.charCode === 110)) {
            index = resultsTree.currentIndex + 1;
            if (index < 0) {
                index = 0;
            }
            if (index < resultsTree.view.rowCount) {
                _selectTreeRow(resultsTree, index);
            }
            event.preventDefault();
            event.stopPropagation();
        }
        //TODO: page up/down
    }
  
    this.onTreeDblClick = function onTreeDblClick(event) {
        this.invokeCurrSelection();
    }

    this.invokeCurrSelection = function invokeCurrSelection() {
        _closePanel();
        _invokeHits(this._treeView.getSelectedHits());
    }
    
    this.editPropertiesCurrSelection = function editPropertiesCurrSelection() {
        _closePanel();
        _editPropertiesHits(this._treeView.getSelectedHits());
    }

    
    //---- internal stuff
    
    this.__defineGetter__("_isMac", function() {
        var isMac = navigator.platform.match(/^Mac/);
        /* Replace getter with the value, so only bother checking the first time. */
        delete this._isMac;
        this._isMac = isMac;
        return isMac;
    });
    
    function _closePanel() {
        document.getElementById("invoketool_panel").hidePopup();
    }
    
    function _extendSelectTreeRow(tree, index) {
        //TODO: fix this to reduce selection when "backing up"
        tree.view.selection.rangedSelect(index, index, true);
        tree.treeBoxObject.ensureRowIsVisible(index);
    }
    
    function _selectTreeRow(tree, index) {
        tree.view.selection.select(index);
        tree.treeBoxObject.ensureRowIsVisible(index);
    }

    /* Open the given hits.
     *
     * @param hits {list of koIToolInfo} The hits to open.
     */
    function _invokeHits(hits) {
        var hit;
        for (var i in hits) {
            ko.toolbox2.invokeTool(hits[i].koTool);
        }
    }

    /* Edit properties of the given tool hits.
     *
     * @param hits {list of koIToolInfo} The hits.
     */
    function _editPropertiesHits(hits) {
        var hit;
        for (var i in hits) {
            ko.toolbox2.editPropertiesTool(hits[i].koTool);
        }
    }


    //---- internal nsITreeView impl
    
    function ToolsTreeView() {
        this._rows = [];
    }
    ToolsTreeView.prototype = new xtk.baseTreeView();
    ToolsTreeView.prototype.constructor = ToolsTreeView;

    ToolsTreeView.prototype.setHits = function(hits) {
        this._hits = hits;
        this.mTotalRows = hits.length;
        if (this.mTree) {
            this.mTree.beginUpdateBatch();
            this.mTree.invalidate();
            this.mTree.endUpdateBatch();
            if (this._hits) {
                this.selection.select(0);
            }
        }
    }
    
    ToolsTreeView.prototype.getSelectedHits = function() {
        var hits = [];
        var rangeCount = this.selection.getRangeCount();
        for (var i = 0; i < rangeCount; ++i) {
            var min = {}, max = {};
            this.selection.getRangeAt(i, min, max);
            for (var j = min.value; j <= max.value; ++j) {
                hits.push(this._hits[j]);
            }
        }
        return hits
    }

    ToolsTreeView.prototype.getCellText = function(rowIdx, column) {
        try {
            return this._hits[rowIdx].name;
        } catch (ex) {
            return "(error: "+ex+")";
        }
    }

    ToolsTreeView.prototype.getImageSrc = function(rowIdx, column) {
        return this._hits[rowIdx].iconUrl;
    }


}).apply(ko.fastopen.invoketool);
