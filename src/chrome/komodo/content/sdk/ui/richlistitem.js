/**
 * @copyright (c) ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR
 * @overview listitem sub module for the ko/ui SDK
 *
 */

var parent = require("./listitem");
var Module = Object.assign({}, parent);
module.exports = Module;

// Main module (module.exports)
(function() {

    this.Model = Object.assign({}, this.Model);

    (function() {

        this.name = "richlistitem";

        this.init = function(label, options = {})
        {
            if (label && typeof label == "object")
            {
                options = label;
                label = null;
            }
            
            if (options.label)
            {
                label = options.label;
            }
            
            this.defaultInit(options);

            if (label)
            {
                var labelElem = require("ko/ui/label").create(label);
                this.addElement(labelElem);
            }
            
            if ( ! this.attributes.value && label)
            {
                this.$element.attr("value", label);
            }
        };

    }).apply(this.Model);

}).apply(Module);
