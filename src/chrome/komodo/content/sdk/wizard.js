/**
 * @copyright (c) 2015 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @overview Row sub module for the ko/ui SDK
 *
 */

function Wizard(element, options) { this.init(element, options); }
(function()
    {
        const $ = require("ko/dom");
        this.type = "wizard";
   
        this.init = function(element = {}, options = {})
        {
            // The only arg passed in might only be options
            if (!element.koDom)
            {
                options = element;
            }
            
            var columnElem = $.create(this.type, options.attributes || {})
            var $element = $(columnElem.toString());
            // if content has been provided append it to the element
            if(element && element.koDom)
            {
                $element.append(element);
            }
            this.$ = $element; // koDom object
            this.element = this.$.element(); // Actual DOM object
        };
   
       /**
        * Append a new wizardpage to the wizard and return it
        *
        * @param {koDom} element, content to append to element on creation.
        * @param {object} options, options to be used on element, OPTIONAL
        *
        * @returns {DOM Object} ko/UI SDK object
        */
       this.addPage = function($ = {}, options = {})
       {
           // The only arg passed in might only be options
           if (!$.koDom)
           {
               options = $;
           }
           
           var columnElem;
           // Create it with options or not
           var page = require("ko/wizard/page").create(options.attributes = {});
           
           if($ && $.koDom)
           {
               page.$.append($);
           }
           this.$.append(page.$);
           return page;
        };
    }
).apply(Wizard.prototype);


/**
 * Create and return a new wizard DOM object
 *
 * @param {Object} options, an options object which contains an attributes object
 *   options = {attributes : {class : "myclass", width : 100, noautohide: true, width: 500, level: "floating"}}
 *
 * @return {object} Wizard, object which contains the koDom object of a
 * wizard (a.k.a <wizard>) element in the element property.
 */
//NOTE allow to accept a Page DOM object or Page module object
// same for addPage
//  Add similar functionality for other UI-ish SDKs

module.exports.create = function(options)
{
    return new Wizard(options);
}
