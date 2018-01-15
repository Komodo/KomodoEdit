var parent = require("./container");
var Module = Object.assign({}, parent);
module.exports = Module;

/**
 * ko/ui spinner element
 * 
 * This module inherits methods and properties from the module it extends.
 * Add a loading spinner for async tasks.
 * 
 * @module ko/ui/spinner
 * @extends module:ko/ui/container~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * var spinner = require("ko/ui/spinner").create();
 * var panel = require("ko/ui/panel").create();
 * panel.addColumn(spinner);
 * panel.open();
 */

(function() {
    
    this.Model = Object.assign({}, this.Model);
    
    /**
     * The model for the row UI element, this is what {@link model:ko/ui/spinner.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/container~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL [hbox]{@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/hbox}
     */

    (function() {
        
        this.name = "hbox";
        this.attributes = { class: "ui-spinner enabled" };
        
        /**
         * Create a new spinner UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/spinner~Model}
         */

        this.init = function()
        {
            this.defaultInit.apply(this, arguments);
        };
        
        /**
         * Hide the element
         * @memberof module:ko/ui/spinner~Model
         */
        this.hide = function ()
        {
            this.$element.hide.apply(this.$element, arguments);
            this.$element.removeClass("enabled");
        };

         /**
         * Show the element
         * @memberof module:ko/ui/spinner~Model
         */
        this.show = function ()
        {
            this.$element.show.apply(this.$element, arguments);
            this.$element.addClass("enabled");
        };
        
    }).apply(this.Model);
    
}).apply(Module);
