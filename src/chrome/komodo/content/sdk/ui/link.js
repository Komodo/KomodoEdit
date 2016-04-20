/**
 * @copyright (c) 2016 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @overview col sub module for the ko/ui SDK
 *
 */

var { Cc, Ci } = require('chrome');
var $      = require("ko/dom");
var parent = require("./element");
var Module = Object.assign({}, parent); 
module.exports = Module;

// Main module (module.exports)
(function() {
    
    this.Model = Object.assign({}, this.Model);
    
    (function() {
        
        this.name = "button";
        this.attributes = { class: "link unstyled" };
        
        this.init = function (value, options)
        {
            var result = this.initWithAttribute("label", value, options);
            
            this.$element.on("click", this.openBrowser.bind(this));
            
            return result;
        };
        
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
