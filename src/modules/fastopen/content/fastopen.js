/* Copyright (c) 2009 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/* Fast open functionality.
 *
 * Defines the "ko.fastopen" namespace.
 */

xtk.include("treeview");

if (typeof(ko) == 'undefined') {
    var ko = {};
}

ko.fastopen = {};
(function() {

    var log = ko.logging.getLogger("fastopen");


    //---- public interface

    this.open_gotofile_dialog = function open_gotofile_dialog() {
        // Make sure the windowtype field (arg #2)
        // matches window@windowtype in gotofile.xul
        ko.windowManager.openOrFocusDialog("chrome://fastopen/content/gotofile.xul",
                                           "komodo_gotofile",
                                           "chrome,centerscreen,titlebar,resizable=yes",
                                           { ko: ko});
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
        }
        this._all_commands = null;
        this.update();
        var queryTextbox = document.getElementById("invoketool_query");
        queryTextbox.focus();
        queryTextbox.select();
    }
    
    this._findTools = function invoketool_findTools(query) {
        var tbSvc = Components.classes["@activestate.com/koToolbox2Service;1"]
            .getService(Components.interfaces.koIToolbox2Service);
        
        // Get ordered list of best language scope (a *list* for
        // multi-language files).
        var currView = ko.views.manager.currentView;
        var langs = [];
        if (currView && currView.koDoc) {
            var koDoc = currView.koDoc;
            langs.push(koDoc.subLanguage);  // lang at current cursor position
            if (langs.indexOf(koDoc.language) === -1) {
                langs.push(koDoc.language);
            }
            currView.koDoc.languageObj.getSubLanguages({}).forEach(function(lang) {
                if (langs.indexOf(lang) === -1) {
                    langs.push(lang);
                }
            });
        }
        
        return tbSvc.findTools(query, langs.length, langs, {});
    }
  
    this._findCommands = function invoketool_findCommands(query) {
        if (!this._all_commands) {
            this._all_commands = [];
            var desc;
            var commandname;
            if (!ko.keybindings.manager.commanditems) {
                // Load the keybinding description information.
                ko.keybindings.manager.parseGlobalData();
            }
            var commanditems = ko.keybindings.manager.commanditems;
            for (var i=0; i < commanditems.length; i++) {
                commandname = commanditems[i].name;
                desc = commanditems[i].desc;
                if (!commandname || !desc) {
                    continue;
                }
                this._all_commands.push(new CommandHit(desc, commandname));
            }
        }

        var commandHits = this._all_commands.slice();
        query = query.toLowerCase();
        var words = query.split(" ");
        // Filter out empty word entries.
        words = words.filter(function(w) { return !word; });
        if (words) {
            var word;
            var matched_all = false;
            var commandDetails;
            commandHits = commandHits.filter(function(cmdhit) {
                            var text = cmdhit.displayText.toLowerCase();
                            if (words.every(function(w) text.indexOf(w) != -1)) {
                                return true;
                            }
                            return false;
                        });
        }
        return commandHits;
    }

    this.update = function invoketool_update() {
        var query = document.getElementById("invoketool_query").value;
        this._treeView.setHits([]);
        if (ko.prefs.getBoolean("invoketool_enable_commands", true)) {
            this._treeView.addHits(this._findCommands(query));
        }
        if (ko.prefs.getBoolean("invoketool_enable_toolbox", true)) {
            this._treeView.addHits(this._findTools(query));
        }
    }

    this.onPanelKeyPress = function onPanelKeyPress(event) {
        return this.onQueryKeyPress(event);

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
        if (keyCode == KeyEvent.DOM_VK_RETURN)
        {
            if (this._isMac ? event.metaKey : event.ctrlKey) {
                this.editPropertiesCurrSelection();
            } else {
                this.invokeCurrSelection();
            }
            event.stopPropagation();
            event.preventDefault();
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

    this.onOptionsPopupShown = function invoketool_onOptionsPopupShown() {
        var commandCheckbox = document.getElementById("invoketool_enable_commands_checkbox");
        commandCheckbox.setAttribute("checked", ko.prefs.getBoolean("invoketool_enable_commands", true));
        var toolboxCheckbox = document.getElementById("invoketool_enable_toolbox_checkbox");
        toolboxCheckbox.setAttribute("checked", ko.prefs.getBoolean("invoketool_enable_toolbox", true));
    }

    this.toggleOptionEnabled = function invoketool_toggleOptionEnabled(prefname) {
        ko.prefs.setBooleanPref(prefname, !ko.prefs.getBoolean(prefname, true));
        this.update();
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
    
    function _selectTreeRow(tree, index) {
        tree.view.selection.select(index);
        tree.treeBoxObject.ensureRowIsVisible(index);
    }

    /* Open the given hits.
     *
     * @param hits {array of [koIToolInfo|CommandHit]} The hits to open.
     */
    function _invokeHits(hits) {
        var hit;
        for (var i = 0; i < hits.length; i++) {
            hit = hits[i];
            try {
                if (hit instanceof CommandHit) {
                    ko.commands.doCommand(hit.commandId);
                } else {
                    ko.toolbox2.invokeTool(hit.koTool);
                }
            } catch(e) {
                log.exception(e, "Failed to invoke tool: ");
            }
        }
    }

    /* Edit properties of the given tool hits.
     *
     * @param hits {list of koIToolInfo} The hits.
     */
    function _editPropertiesHits(hits) {
        for (var i in hits) {
            ko.toolbox2.editPropertiesTool(hits[i].koTool);
        }
    }


    //---- internal nsITreeView impl

    function CommandHit(name, commandId) {
        this.name = name;
        this.subDir = commandId;
        this.commandId = commandId;
        this.displayText = name + " " + commandId;
    }
    CommandHit.prototype = {
        iconUrl: "chrome://fugue/skin/icons/external.png",
    }

    function ToolsTreeView() {
        this._rows = [];
    }
    ToolsTreeView.prototype = new xtk.baseTreeView();
    ToolsTreeView.prototype.constructor = ToolsTreeView;

    /**
     * Hits are objects that have the following properties:
     * {
     *   name: The name of the item,
     *   subDir: Additional text info - displayed after the name,
     *   iconUrl: URL to an chrome icon to display for the hit.
     * }
     */
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
    ToolsTreeView.prototype.addHits = function(hits) {
        var oldlength = this._hits.length;
        this._hits = this._hits.concat(hits);
        this.mTotalRows = this._hits.length;
        if (this.mTree) {
            this.mTree.rowCountChanged(oldlength, hits.length);
            if (!oldlength && this._hits) {
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
                if (this._hits[j]) {
                    // Bug 100181: Don't push non-existent names.
                    hits.push(this._hits[j]);
                }
            }
        }
        return hits
    }

    ToolsTreeView.prototype.getCellText = function(rowIdx, column) {
        try {
            var hit = this._hits[rowIdx];
            var text = hit.name;
            if (hit.subDir) {
                text += " \u2014 " + hit.subDir;
            }
            return text;
        } catch (ex) {
            return "(error: "+ex+")";
        }
    }

    ToolsTreeView.prototype.getImageSrc = function(rowIdx, column) {
        return this._hits[rowIdx].iconUrl;
    }


}).apply(ko.fastopen.invoketool);
