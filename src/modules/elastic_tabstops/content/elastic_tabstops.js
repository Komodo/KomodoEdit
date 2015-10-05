(function() {
    const log = require("ko/logging").getLogger("elastic_tabstops");
    const {Cc, Ci} = require("chrome");
    const views = require("ko/views");
    const editor = require("ko/editor");
    const prefs = ko.prefs;
    
    /** The preference that enables/disables elastic tabstops. */
    const PREF_ENABLE_ELASTIC_TABSTOPS = "enableElasticTabstops";
    
    // By default, tabstops are at least 32 pixels plus 12 pixels of padding.
    var tab_width_minimum = 32;
    var tab_width_padding = 12;

    /** Loads elastic tabstops. */
    this.load = function() {
        // Listen for enable/disable elastic tabstops preference.
        prefs.prefObserverService.addObserver(this, PREF_ENABLE_ELASTIC_TABSTOPS, false);
        
        // Enable elastic tabstops in new views as necessary.
        window.addEventListener('view_document_attached', this._onViewDocumentAttached);
        window.addEventListener('view_document_detaching', this._onViewDocumentDetaching);
        window.addEventListener('unload', this._onUnload);
        // Enable elastic tabstops on all initial views because
        // "view_document_attached" is not emitted on startup.
        // TODO: this is a hack.
        window.setTimeout(function() {
            this.observe(null, PREF_ENABLE_ELASTIC_TABSTOPS, null);
        }.bind(this), 2500);
        
        log.setLevel(ko.logging.LOG_INFO);
        log.info("Elastic tabstops loaded.");
    }
    
    /** Unloads elastic tabstops. */
    this.unload = function() {
        prefs.prefObserverService.removeObserver(this, PREF_ENABLE_ELASTIC_TABSTOPS);
        log.info("Elastic tabstops unloaded.");
    }
    
    // Beginning of clone of C++ version of
    // https://github.com/nickgravgaard/ElasticTabstopsForScintilla
    
    this._getLineStart = function(scimoz, pos) {
        var line = scimoz.lineFromPosition(pos);
        return scimoz.positionFromLine(line);
    }
    
    this._getLineEnd = function(scimoz, pos) {
        var line = scimoz.lineFromPosition(pos);
        return scimoz.getLineEndPosition(line);
    }
    
    this._isLineEnd = function(scimoz, pos) {
        var line = scimoz.lineFromPosition(pos);
        var endPos = scimoz.getLineEndPosition(line);
        return pos == endPos;
    }
    
    this._getTextWidth = function(scimoz, start, end) {
        var range = scimoz.getTextRange(start, end);
        var style = scimoz.getStyleAt(start);
        return scimoz.textWidth(style, range);
    }
    
    this._calcTabWidth = function(text_width_in_tab) {
        if (text_width_in_tab < tab_width_minimum) {
            text_width_in_tab = tab_width_minimum;
        }
        return text_width_in_tab + tab_width_padding;
    }
    
    this._changeLine = function(scimoz, location, forward) { // C++ has `location` as `int&`
        var line = scimoz.lineFromPosition(location.value);
        if (forward) {
            location.value = scimoz.positionFromLine(line + 1);
        } else {
            if (line <= 0) {
                return false;
            }
            location.value = scimoz.positionFromLine(line - 1);
        }
        return location.value >= 0;
    }
    
    this._getBlockBoundary = function(scimoz, location, forward) { // C++ has `location` as `int&`
        var max_tabs = 0;
        var orig_line = true;
        
        location.value = this._getLineStart(scimoz, location.value);
        do {
            var tabs_on_line = 0;
            
            var current_pos = location.value;
            var current_char = scimoz.getCharAt(current_pos);
            var current_char_ends_line = this._isLineEnd(scimoz, current_pos);
            
            while (current_char && !current_char_ends_line) {
                if (current_char == 9) { // '\t'
                    tabs_on_line++;
                    if (tabs_on_line > max_tabs) {
                        max_tabs = tabs_on_line;
                    }
                }
                current_pos = scimoz.positionAfter(current_pos);
                current_char = scimoz.getCharAt(current_pos);
                current_char_ends_line = this._isLineEnd(scimoz, current_pos);
            }
            if (tabs_on_line == 0 && !orig_line) {
                return max_tabs;
            }
            orig_line = false;
        } while (this._changeLine(scimoz, location, forward));
        return max_tabs;
    }
    
    this._getNOfTabsBetween = function(scimoz, start, end) {
        var current_pos = {value: this._getLineStart(scimoz, start)};
        var max_tabs = 0;
        
        do {
            var current_char = scimoz.getCharAt(current_pos.value);
            var current_char_ends_line = this._isLineEnd(scimoz, current_pos.value);
            
            var tabs_on_line = 0;
            while (current_char && !current_char_ends_line) {
                if (current_char == 9) { // '\t'
                    tabs_on_line++;
                    if (tabs_on_line > max_tabs) {
                        max_tabs = tabs_on_line;
                    }
                }
                current_pos.value = scimoz.positionAfter(current_pos.value);
                current_char = scimoz.getCharAt(current_pos.value);
                current_char_ends_line = this._isLineEnd(scimoz, current_pos.value);
            }
        } while (this._changeLine(scimoz, current_pos, true) && current_pos.value < end);
        return max_tabs;
    }
    
    this._stretchTabstops = function(scimoz, block_start_linenum, block_nof_lines, max_tabs) {
        var lines = {};
        var grid = {};
        for (let l = 0; l < block_nof_lines; l++) {
            grid[l] = {};
            for (let t = 0; t <= max_tabs; t++) {
                grid[l][t] = {text_width_pix: {value: 0}, widest_width_pix: null, ends_in_tab: false};
            }
            lines[l] = {num_tabs: 0};
        }
        
        // Get width of text in cells.
        for (let l = 0; l < block_nof_lines; l++) { // for each line
            var text_width_in_tab = 0;
            var current_line_num = block_start_linenum + l;
            var current_tab_num = 0;
            var cell_empty = true;
            
            var current_pos = scimoz.positionFromLine(current_line_num);
            var cell_start = current_pos;
            var current_char = scimoz.getCharAt(current_pos);
            var current_char_ends_line = this._isLineEnd(scimoz, current_pos);
            // maybe change this to search forwards for tabs/newlines
            
            while (current_char) {
                if (current_char_ends_line) {
                    grid[l][current_tab_num].ends_in_tab = false;
                    text_width_in_tab = 0;
                    break;
                } else if (current_char == 9) { // '\t'
                    if (!cell_empty) {
                        text_width_in_tab = this._getTextWidth(scimoz, cell_start, current_pos);
                    }
                    grid[l][current_tab_num].ends_in_tab = true;
                    grid[l][current_tab_num].text_width_pix.value = this._calcTabWidth(text_width_in_tab);
                    current_tab_num++;
                    lines[l].num_tabs++;
                    text_width_in_tab = 0;
                    cell_empty = true;
                } else {
                    if (cell_empty) {
                        cell_start = current_pos;
                        cell_empty = false;
                    }
                }
                current_pos = scimoz.positionAfter(current_pos);
                current_char = scimoz.getCharAt(current_pos);
                current_char_ends_line = this._isLineEnd(scimoz, current_pos);
            }
        }
        
        // Find columns blocks and stretch to fit the widest cell.
        for (let t = 0; t < max_tabs; t++) { // for each column
            var starting_new_block = true
            var first_line_in_block = 0;
            var max_width = 0;
            for (let l = 0; l < block_nof_lines; l++) { // for each line
                if (starting_new_block) {
                    starting_new_block = false;
                    first_line_in_block = l;
                    max_width = 0;
                }
                if (grid[l][t].ends_in_tab) {
                    grid[l][t].widest_width_pix = grid[first_line_in_block][t].text_width_pix; // point widestWidthPix at first
                    if (grid[l][t].text_width_pix.value > max_width) {
                        max_width = grid[l][t].text_width_pix.value;
                        grid[first_line_in_block][t].text_width_pix.value = max_width;
                    }
                } else { // end column block
                    starting_new_block = true;
                }
            }
        }
        
        // Set tabstops.
        for (let l = 0; l < block_nof_lines; l++) { // for each line
            var current_line_num = block_start_linenum + l;
            var acc_tabstop = 0;
            
            scimoz.clearTabStops(current_line_num);
            
            for (let t = 0; t < lines[l].num_tabs; t++) {
                if (grid[l][t].widest_width_pix) {
                    acc_tabstop += grid[l][t].widest_width_pix.value;
                    scimoz.addTabStop(current_line_num, acc_tabstop);
                    //log.debug("Added tab stop on line " + current_line_num + " at " + acc_tabstop + " pixels");
                } else {
                    break;
                }
            }
        }
    }
    
    this._onModify = function(scimoz, start, end) {
        //log.debug("Updating from " + start.value + " to " + end.value);
        var max_tabs_between = this._getNOfTabsBetween(scimoz, start.value, end.value);
        //log.debug("Max tabs between: " + max_tabs_between);
        var max_tabs_backwards = this._getBlockBoundary(scimoz, start, false);
        //log.debug("Max tabs backwards: " + max_tabs_backwards);
        var max_tabs_forwards = this._getBlockBoundary(scimoz, end, true);
        //log.debug("Max tabs forwards: " + max_tabs_forwards);
        var max_tabs = Math.max(Math.max(max_tabs_between, max_tabs_backwards), max_tabs_forwards);
        //log.debug("Max tabs: " + max_tabs);
        
        var block_start_linenum = scimoz.lineFromPosition(start.value);
        var block_end_linenum = scimoz.lineFromPosition(end.value);
        var block_nof_lines = (block_end_linenum - block_start_linenum) + 1;
        //log.debug("Stretching tabstops from line " + block_start_linenum + " to " + (block_start_linenum + block_nof_lines));
        
        this._stretchTabstops(scimoz, block_start_linenum, block_nof_lines, max_tabs);
    }
    
    // If text has been added or removed, update the tabstops.
    this._onModifiedHandler = function(position, modification_type, text) {
        if (modification_type & Ci.ISciMoz.SC_MOD_INSERTTEXT) {
            //log.debug("Text added. Updating tabstops.");
            this._onModify(editor.scimoz(), {value: position}, {value: position + text.length});
        } else if (modification_type & Ci.ISciMoz.SC_MOD_DELETETEXT) {
            //log.debug("Text removed. Updating tabstops.");
            this._onModify(editor.scimoz(), {value: position}, {value: position});
        }
    }
    
    // End of clone of C++ version of
    // https://github.com/nickgravgaard/ElasticTabstopsForScintilla
    
    /**
     * Enables elastic tabstops in the given view.
     * @param view The view to enable elastic tabstops in.
     */
    this._enableElasticTabstops = function(view) {
        view.addModifiedHandler(this._onModifiedHandler, this, 1000,
                                Ci.ISciMoz.SC_MOD_INSERTTEXT |
                                Ci.ISciMoz.SC_MOD_DELETETEXT);
        this._onModify(view.scimoz, {value: 0}, {value: view.scimoz.length});
    }
    
    /**
     * Disables elastic tabstops in the given view.
     * @param view The view to disable elastic tabstops in.
     */
    this._disableElasticTabstops = function(view) {
        if (view.getAttribute('type') != 'editor') {
            return;
        }
        try {
            view.removeModifiedHandler(this._onModifiedHandler);
            // Clear tab stops unless detaching the view.
            var scimoz = view.scimoz;
            for (let i = 0; i < scimoz.lineCount; i++) {
                scimoz.clearTabStops(i);
            }
        } catch (e) {
            // Elastic tabstops were not enabled in the first place, so there is
            // no SCN_MODIFIED handler to unregister.
        }
    }
    
    /**
     * Enables elastic tabstops in new views.
     * @param event The event fired when creating a new view.
     */
    this._onViewDocumentAttached = function(event) {
        var view = event.originalTarget;
        if (view.getAttribute('type') != 'editor'
            || !prefs.getBoolean(PREF_ENABLE_ELASTIC_TABSTOPS)) {
            return;
        }
        //log.debug("Registering elastic tabstops handler to attached view");
        this._enableElasticTabstops(view);
    }.bind(this)
    
    /**
     * Disables elastic tabstops in closing views.
     * @param event The event fired before deleting a view.
     */
    this._onViewDocumentDetaching = function(event) {
        var view = event.originalTarget;
        //log.debug("Unregistering elastic tabstops handler from detaching view");
        this._disableElasticTabstops(view);
    }.bind(this)
    
    /**
     * Stop listening to view events as the window shuts down.
     */
    this._onUnload = function() {
        window.removeEventListener('view_document_attached', this._onViewDocumentAttached, false);
        window.removeEventListener('view_document_detaching', this._onViewDocumentDetaching, false);
        window.removeEventListener('unload', this._onUnload, false);
    }.bind(this);
    
    /**
     * Listen for elastic tabstops preference changes.
     */
    this.observe = function(subject, topic, data) {
        if (topic == PREF_ENABLE_ELASTIC_TABSTOPS) {
            var enabled = prefs.getBoolean(PREF_ENABLE_ELASTIC_TABSTOPS);
            for (let view of views.editors()) {
                if (enabled) {
                    this._enableElasticTabstops(view);
                } else {
                    this._disableElasticTabstops(view);
                }
            }
        }
    }
}).apply(module.exports)
