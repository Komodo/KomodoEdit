var parent = require("./container");
var Module = Object.assign({}, parent); 
module.exports = Module;


/**
 * ko/ui wizardpage element
 * 
 * This module inherits methods and properties from the module it extends.
 * Quickly generate wizard page containers for [XUL wizard](https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/wizard)
 * 
 * @module ko/ui/wizardpage
 * @extends module:ko/ui/container~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * var wizard = $("<wizard>").attr("flex", "1");
 * var wizardpage = require("ko/ui/wizardpage").create();
 * wizard.append(wizardpage);
 * //Now start adding things to the wizardpage container
 */

(function() {
    
    this.Model = Object.assign({}, this.Model);
    
    /**
     * The model for the row UI element, this is what {@link model:ko/ui/wizardpage.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/container~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL [wizardpage]{@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/wizardpage}
     */

    (function() {
        
        // Set the element name
        this.name = "wizardpage";
        this.attributes = { style: "overflow: -moz-hidden-unscrollable" };
        
        /**
         * Create a new wizardpage UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/wizardpage~Model}
         */

        // .. that's it, all the rest is handled by the parent(s)
        
    }).apply(this.Model); // extend parent Model
    
}).apply(Module);