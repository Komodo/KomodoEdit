/**
 * @copyright (c) 2016 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @overview listheader sub module for the ko/ui SDK
 */

var parent = require("./element");
var Module = Object.assign({}, parent);
module.exports = Module;

// Main module (module.exports)
(function() {

    this.Model = Object.assign({}, this.Model);

    (function() {

        this.name = "listheader";

        this.init = this.initWithLabel;

    }).apply(this.Model);

}).apply(Module);

