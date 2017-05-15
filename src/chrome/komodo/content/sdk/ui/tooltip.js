/**
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR
 */


var parent = require("./panel");
var Module = Object.assign({}, parent);
module.exports = Module;

(function() {

    this.Model = Object.assign({}, this.Model);

    (function() {

        this.name = "tooltip";

    }).apply(this.Model);

}).apply(Module);
