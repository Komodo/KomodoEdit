/**
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR
 */


var parent = require("./container");
var Module = Object.assign({}, parent);
module.exports = Module;

(function() {

    this.Model = Object.assign({}, this.Model);

    (function() {

        this.name = "deck";

        this.index = function(value)
        {
            if (value !== undefined)
                this.element.selectedIndex = value;
            return this.element.selectedIndex;
        };

        this.panel = function(value)
        {
            if (value)
                this.element.selectedPanel = value;
            return this.element.selectedPanel;
        };

    }).apply(this.Model);

}).apply(Module);
