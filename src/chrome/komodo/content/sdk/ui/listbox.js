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
    
    (function() {
        
        this.name = "listbox";
        
        this.init = function(listitems = [], options = {})
        {
            if ( ! Array.isArray(listitems) && typeof listitems == "object")
            {
                options = listitems;
                listitems = null;
            }
            
            if ("listitems" in options)
            {
                listitems = options.listitems;
            }
            
            this.options = options;
            this.$element = $($.create(this.name, options.attributes || {}).toString());
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
            if ("isSdkElement" in item)
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
        
        this.getSelectedItems = function()
        {
            return this.element.selectedItems;
        }
        
        this.removeAllItems = function()
        {
            var rows = this.element.getRowCount();
            console.log("deleting this many: " + rows);
            for ( let i = 0; i < rows; i++ )
            {
                console.log(this.element. getItemAtIndex(0));
                this.element.removeItemAt(0);
            }
        };
        
        /**
         * Select one or more items in the list
         * If singleSelect is true, only the item passed in will be select
         * If it's false AND the list is multi select then it's added to the
         * list of selected items
         *
         * @argument  @argument {ko/ui/obj | ko/dom/obj | DOM | Object} item
         *      Item to be selected
         * @argument {boolean}  singleSelect    only select the given item
         */
        this.selectItem = function(item,singleSelect)
        {
            if( singleSelect )
            {
                if ("isSdkElement" in item)
                {
                    this.element.selectItem(item.element);
                    this.element.ensureElementIsVisible(item.element);
                }
                else if ("koDom" in item)
                {
                    this.element.selectItem(item.element());
                    this.element.ensureElementIsVisible(item.element());
                }
                else if ("nodeName" in item)
                {
                    this.element.selectItem(item);
                    this.element.ensureElementIsVisible(item);
                }
            }
            else
            {
                if ("isSdkElement" in item)
                {
                    this.element.addItemToSelection(item.element);
                    //this.element.ensureElementIsVisible(item.element);
                }
                else if ("koDom" in item)
                {
                    this.element.addItemToSelection(item.element());
                    //this.element.ensureElementIsVisible(item.element());
                }
                else if ("nodeName" in item)
                {
                    this.element.addItemToSelection(item);
                    //this.element.ensureElementIsVisible(item);
                }
            }
        };
        
    }).apply(this.Model); 
    
}).apply(Module);

