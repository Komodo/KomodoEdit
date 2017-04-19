/**
 * @copyright (c) 2016 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @overview Row sub module for the ko/ui SDK
 */

var $ = require("ko/dom");
var parent = require("./element");
var Module = Object.assign({}, parent);
var log = require("ko/logging").getLogger("sdk/ui/listbox");
//log.setLevel(require("ko/logging").LOG_DEBUG);
module.exports = Module;

// Main module (module.exports)
(function() {
    
    this.Model = Object.assign({}, this.Model);
    
    this.listhead = null;
    this.listcols = null;
    
    (function() {
        
        this.name = "listbox";
        
        this.init = function(listitems = [], options = {})
        {
            if ( ! Array.isArray(listitems) && typeof listitems == "object")
            {
                options = listitems;
                listitems = null;
            }
            
            this.parseOptions(options);
            options = this.options;

            if ("listitems" in options)
            {
                listitems = options.listitems;
            }
            
            this.$element = $($.create(this.name, this.attributes).toString());
            this.$element.addClass("ui-" + this.name);
            this.element = this.$element.element();
            
            if (listitems && Array.isArray(listitems))
            {
                this.addListItems(listitems);
            }
            else if (listitems && ! Array.isArray(listitems))
            {
                log.warn("List items must be in an array.  Failed to add list "+
                         "items to listbox.");
            }
            
            if ("listheaders" in options)
            {
                this.addListHeaders(options.listheaders);
            }
            
            if ("listcols" in options)
            {
                this.addListCols(options.listcols);
            }
        };
        
        this.addListItems = function (entries)
        {
            for (let entry of entries) {
                this.addListItem(entry);
            }
        };
        
          /**
         * Add an item to the container
         *
         * @argument {ko/ui/obj | ko/dom/obj | DOM | Object} item item to be added
         * to the container.
         *
         * Object refers to an Options object used through this SDK. The options
         * should contain an attributes property to assign a label at the very
         * least:
         *
         *  {
         *      attributes:
         *      {
         *          label:"itemLable"
         *      }
         *  }
         */ 
        this.addListItem = function (item)
        {
            var element;
            if (typeof item == "string") {
                element = require("ko/ui/listitem").create(item).element;
            }
            else if ("isSdkElement" in item)
            {
                element = item.element;
            }
            else if ("koDom" in item)
            {
                element = item.element();
            }
            else if ("nodeName" in item)
            {
                element = item;
            }
            else
            {
                var type = item.type || "listitem";
                element = require('./' + type).create(item).element;
            }
            
            this.$element.append(element);
            
            if (element.getAttribute("selected") == "true" && "selectedItem" in this.element)
            {
                this.element.selectedItem = element;
            }
        };
        
        this.addListHeaders = function(listheaders)
        {
            for (let listhead of listheaders)
            {
                this.addListHeader(listhead);
            }
        };
        
        this.addListHeader = function(header)
        {
            if ( ! this.listhead)
            {
                this.listhead = require("./listhead").create();
                this.$element.append(this.listhead.$element);
            }
            
            this.listhead.addListHeader.apply(this.listhead, arguments);
        };
        
        this.addListCols = function(listcols)
        {
            for (let listcol of listcols)
            {
                this.addListCol(listcol);
            }
        };
        
        this.addListCol = function()
        {
            if ( ! this.listcols)
            {
                this.listcols = require("./listcols").create();
                this.$element.append(this.listcols.$element);
            }
            
            this.listcols.addListCol.apply(this.listcols, arguments);
        };
        
        this.setSelectedIndex = function(index)
        {
            this.element.selectedIndex = index;
        };

        this.getSelectedItems = function()
        {
            return this.element.selectedItems;
        };
        
        this.getSelectedItem = function()
        {
            return this.element.selectedItem;
        };
        
        this.removeAllItems = function()
        {
            if ( ! this.element.removeItemAt)
            {
                this.$element.empty();
                return;
            }

            var rows = this.element.getRowCount();
            for ( let i = 0; i < rows; i++ )
            {
                this.element.removeItemAt(0);
            }
        };
        
        this.value = function()
        {
            var item = this.getSelectedItem();
            if ( ! item)
                return "";

            return item.hasAttribute("value") ? item.getAttribute("value") : item.getAttribute("label");
        };

    }).apply(this.Model); 
    
}).apply(Module);

