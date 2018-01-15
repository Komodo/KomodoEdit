var parent = require("./container");
var Module = Object.assign({}, parent);
module.exports = Module;

/**
 * ko/ui filepath element
 * 
 * This module inherits methods and properties from the module it extends.  Using
 * the module:ko/ui/filepath.create function will return a element with a text
 * field and a button.  The button opens a dialog to search for and select some
 * filepath based on the type passed in; "file", "dir", "exe", "files", "remote".
 *
 * @class Model
 * 
 * @module ko/ui/filepath
 * @extends module:ko/ui/container~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * var filepath = require("ko/ui/filepath").create({filetype:"file"});
 * panel = require("ko/ui/panel").create()
 * panel.addRow(filepath);
 * panel.open();
 * // userselects a path
 * filepath.value(); //outputs selected path.
 */

(function() {
    
    this.Model = Object.assign({}, this.Model);
    
    /**
     * The model for the row UI element, this is what {@link model:ko/ui/filepath.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/container~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A Xul element
     */

    (function() {
        
        this.name = "hbox";
        this.attributes = { class: "ui-filepath" };
        
        /**
         * Create a new filepath UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options, must conatin
         *                                      a "type" attribute of type "file", "dir", "exe", "files", "remote".
         *
         * @returns {module:ko/ui/filepath~Model}
         */

        this.init = function()
        {
            this.defaultInit.apply(this, arguments);
            this.textbox = require("ko/ui/textbox").create({ attributes: this.attributes });
            
            var button = require("ko/ui/button").create("...");
            button.onCommand(() =>
            {
                var ko = require("ko/windows").getMain().ko;
                
                var type = this.attributes.filetype || this.options.filetype || "file";
                var value = this.textbox.value();
                
                var filter = this.attributes.filter || null;
                var filters = this.attributes.filters || null;

                switch (type)
                {
                    default:
                    case "file":
                        this.textbox.value(ko.filepicker.browseForFile(value, null, null, filter, filters));
                        break;
                    case "dir":
                        this.textbox.value(ko.filepicker.browseForDir(value));
                        break;
                    case "exe":
                        this.textbox.value(ko.filepicker.browseForExeFile(value));
                        break;
                    case "files":
                        this.textbox.value(ko.filepicker.browseForFiles(value));
                        break;
                    case "remote":
                        this.textbox.value(ko.filepicker.browseForRemoteDir(value));
                        break;
                }

                this.textbox.$element.trigger("input");
            });
            
            this.addElement(this.textbox);
            this.addElement(button);
        };
        
        /**
         * Return or set selected state
         *
         * @returns {String} The set value
         * @memberof module:ko/ui/filepath~Model
         */
        this.value = function() { return this.textbox.value.apply(this.textbox, arguments); };
        
    }).apply(this.Model);
    
}).apply(Module);
