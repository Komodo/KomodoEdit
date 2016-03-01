/**
 * @copyright (c) 2015 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @overview Row sub module for the ko/ui SDK
 *
 */

function Wizard($element = {}, options = {}) { this.init($element, options); }
(function()
    {
        const $ = require("ko/dom");
        this.type = "wizard";
   
        this.init = function($element = {}, options = {})
        {
            // The only arg passed in might only be options
            if (!$element.koDom)
            {
                options = $element;
            }
            var newElem = $.create(this.type, options.attributes || {})
            var $newElem = $(newElem.toString());
            // if content has been provided append it to the element
            if($element && $element.koDom)
            {
                $newElem.append($element);
            }
            this.$elem = $newElem; // koDom object
            this.element = this.$elem.element; // Actual DOM object
        };
   
       /**
        * Append a new wizardpage to the wizard and return it
        *
        * @param {koDom} element, content to append to element on creation.
        * @param {object} options, options to be used on element, OPTIONAL
        *
        * @returns {DOM Object} ko/UI SDK object
        */
       this.addPage = function wizard_addPage($element = {}, options = {})
       {
           // The only arg passed in might only be options
           if (!$element.koDom)
           {
               options =$element;
           }
           
           // Create it with options or not
           var page = require("ko/wizard/page").create(options.attributes || {});
           
           if($element && $element.koDom)
           {
               page.$elem.append($element);
           }
           this.$elem.append(page.$elem);
           return page;
        };
        
        /**
         * Open the wizard dialog in a particular location on the screen.
         *  Example of args object to open Wizard with:
         *  {
         *      args:
         *      {
         *          anchor: element to attach to,
         *          position: position relative to anchor,
         *          x: relative to top left of anchor,
         *          y: relative to top left of anchor
         *      }
         *  }
         *
         *  You can also pass attributes in using the same object.  These are
         *  used on the Panel created by this method to house the wizard:
         *  {
         *      args:
         *      {
         *          ...    
         *      },
         *      attributes:
         *      {
         *          consumeoutsideclicks: true, //default
         *          backdrag = options.attributes.backdrag || true //default
         *          ...
         *      }
         *  }
         *  
         * @param {object} options, args and attributes for opening the wizard
         *
         * @returns {koDom} panel, a handle to the panel object created.
         *
         */
        this.open = function(options = {})
        {
            if(!options.attributes)
            {
                options.attributes = {};
            }
            options.attributes.consumeoutsideclicks = options.attributes.consumeoutsideclicks || true;
            options.attributes.backdrag = options.attributes.backdrag || true;
            var panel = require("ko/ui/panel").create(options.attributes = {});
            panel.$elem.append(this.$elem);
            this.parent = panel;
            panel.open(options.args = {});
            return this.parent;
        }
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

module.exports.create = function wizard_create($element = {}, options = {})
{
    return new Wizard($element, options);
}
