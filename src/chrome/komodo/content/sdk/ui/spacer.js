var parent = require("./element");
var Module = Object.assign({}, parent);
module.exports = Module;


/**
 * ko/ui spacer element
 * 
 * This module inherits methods and properties from the module it extends.
 * Quickly generate a separator for you UI.
 * 
 * @module ko/ui/spacer
 * @extends module:ko/ui/element~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR
 * @example
 * var spacer = require("ko/ui/spacer").create();
 * var label1 = require("ko/ui/label").create("Label1");
 * var label2 = require("ko/ui/label").create("label2");
 * var panel = require("ko/ui/panel").create();
 * panel.addColumn([spacer,label1,label2]);
 * panel.open();
 */

(function() {

    this.Model = Object.assign({}, this.Model);
    
    /**
     * The model for the row UI element, this is what {@link model:ko/ui/spacer.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/element~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL [spacer]{@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/spacer}
     */

    (function() {

        this.name = "spacer";
        
        /**
         * Create a new spacer UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/spacer~Model}
         */

    }).apply(this.Model);

}).apply(Module);
