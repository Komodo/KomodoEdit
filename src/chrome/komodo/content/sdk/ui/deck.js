var parent = require("./container");
var Module = Object.assign({}, parent);
module.exports = Module;
/**
 * ko/ui deck element
 * 
 * This module inherits methods and properties from the module it extends.
 * 
 * @module ko/ui/deck
 * @extends module:ko/ui/container~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR
 * @example
 * var deck = require("ko/ui/deck").create();
 * deck.index(1);
 */
(function() {

    this.Model = Object.assign({}, this.Model);
    /**
     * The model for the row UI element, this is what {@link model:ko/ui/deck.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/container~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL [deck]{@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/deck}
     */
    (function() {

        this.name = "deck";
        /**
         * Create a new deck UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/deck~Model}
         */
        
        /**
         * Gets and sets the index of the currently selected panel.
         * The first item is at index 0.
         *
         * @param {integer} value - index to be selected.  See [deck.selectedPanel]{@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/deck#a-selectedIndex}
         * @memberof module:ko/ui/deck~Model
         */
        this.index = function(value)
        {
            if (value !== undefined)
                this.element.selectedIndex = value;
            return this.element.selectedIndex;
        };
        
        /**
         * Gets and sets the index of the currently selected panel.
         * The first item is at index 0.
         *
         * @param {element} value - A panel element to be set.  See [deck.selectedPanel]{@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/deck#p-deck.selectedPanel}
         * @memberof module:ko/ui/deck~Model
         */
        this.panel = function(value)
        {
            if (value)
                this.element.selectedPanel = value;
            return this.element.selectedPanel;
        };

    }).apply(this.Model);

}).apply(Module);
