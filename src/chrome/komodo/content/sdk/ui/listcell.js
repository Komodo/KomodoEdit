/**
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR
 */

var parent = require("./element");
var Module = Object.assign({}, parent);
module.exports = Module;

// Main module (module.exports)
(function() {

    this.Model = Object.assign({}, this.Model);

    (function() {

        this.name = "listcell";

        this.init = this.initWithLabel;

    }).apply(this.Model);

}).apply(Module);

