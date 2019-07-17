var { Cc, Ci } = require('chrome');
var $      = require("ko/dom");
var parent = require("./element");
var Module = Object.assign({}, parent);
module.exports = Module;


/**
 * ko/ui link element
 * 
 * Create a custom link that you can append to any {@link module:ko/ui/container~Model}
 * and have it open in a browser.
 * This module inherits methods and properties from the module it extends.
 *
 * @module ko/ui/link
 * @extends module:ko/ui/element~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * var link = require("ko/ui/link").create("Komodo IDE",{attributes:{href:"http://www.komodoide.com"}});
 * panel = require("ko/ui/panel").create()
 * panel.addRow(link);
 * panel.open();
 */

(function() {

    this.Model = Object.assign({}, this.Model);
    
    /**
     * The model for the row UI element, this is what {@link model:ko/ui/link.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/element~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL [button]{@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/button}
     */

    (function() {

        this.name = "button";
        this.attributes = { class: "link unstyled" };
        
        /**
         * Create a new link UI element
         * 
         * @name create
         * @method
         * @param {String}          link        Link to be opened
         * @param  {object}         [options]   An object containing attributes and options
         *                                      Must have an `href` attribute and it must include the protocol. ie. `http://`.
         * 
         * @returns {module:ko/ui/link~Model}
         *
         * 
         */

        this.init = function (value, options)
        {
            var result = this.initWithAttribute("label", value, options);

            this.$element.on("click", this.openBrowser.bind(this));

            return result;
        };
        
        /**
         * Open the link in a browser programmatically
         */
        this.openBrowser = function ()
        {
            if ( ! this.attributes.href)
                return;

            var ioservice = Cc["@mozilla.org/network/io-service;1"]
                                      .getService(Ci.nsIIOService);
            var uriToOpen = ioservice.newURI(this.attributes.href, null, null);
            var extps = Cc["@mozilla.org/uriloader/external-protocol-service;1"]
                                  .getService(Ci.nsIExternalProtocolService);

            extps.loadURI(uriToOpen, null);
        };

    }).apply(this.Model);

}).apply(Module);
