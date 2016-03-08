/**
 * @copyright (c) 2015 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @overview col sub module for the ko/ui SDK
 *
 */

/**
 * "declaration" of the button class.  Uses the init() function as a constructor
 */
function Button(label, command, options = {}) { this.init(label, command, options); }

(function()
    {
        var $ = require("ko/dom");
        this.type = "button"; // Set in init
        
        this.init = function(label, command, options = {attributes:{}})
        {
            if ((typeof label) == "object")
            {
                options = label;
            }
            else
            {
                options.attributes.label = label;
                options.attributes.command = command;
            }
            
            if ( ! ("label" in options.attributes))
            {
                throw new exceptionMissingProp("label");
            }
    
            var newElem = $.create(this.type, options.attributes || {})
            var $newElem = $(newElem.toString());
            this.$elem = $newElem; // koDom object
            this.element = this.$elem.element.bind(this.$elem); // Actual DOM object
        };
        
        /**
        * Exception that is thrown when a required property was not defined
        */
        function exceptionMissingProp(prop)
        {
            this.message = "Button registration failed due to missing " + prop + " property";
        }
        this.exceptionMissingProp = exceptionMissingProp;
    }
).apply(Button.prototype);

/**
 * Create an instance of a button object 
 *
 * @param   {String|Object} label       Optionally this can hold the entire opts object, with a label and command entry
 * @param   {Function}      command     The callback function
 * @param   {Object}        opts        Options
 * 
 * @returns {Object}        Button      the new button SDK object
 */
module.exports.create = function button_create(label, command, options = {})
{
    return new Button(label, command, options);
}
