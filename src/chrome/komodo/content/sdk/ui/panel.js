/**
 * @copyright (c) 2015 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author CareyH
 * @overview Page sub module for the wizard SDK module
 *
 */

/**
 * "declaration" of the Row class.  Uses the init() function as a constructor
 */
function Panel($element = {}, options = {}) { this.init($element, options) };
(function()
    {
        var $ = require("ko/dom");
        this.type = "panel";

        /**
         * Initialize the properties of the object being passed to the user
         */
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
         * Insert content to the panel
         *
         * @param {koDom} content, a koDom object to be inserted into the panel
         */
        this.addContent = function panel_addContent($content)
        {
            this.$elem.append($content);
        }
        
        /**
         * Show the panel.
         *
         * @param {object} options, options object should contain the following:
         *   
         *    {
         *        anchor : dom object to anchor to,
         *        position:   "before_start, before_end, after_start, after_end, start_before, start_after, end_before, end_after, overlap, and after_pointer",
         *        x : number,
         *        y : number,
         *        isContextMenu : bool,
         *        attributesOverride : bool,
         *        triggerEvent : event)
         *    }
         *    ref: https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/Method/openPopup
         * 
         */
        this.open = function panel_open(args = {})
        {
            var anchor =  args.anchor || null;
            var position = args.position || null;
            var x = args.x || 0;
            var y = args.y || 0;
            var isContextMenu = args.isContextMenu || false;
            var attributesOverride = args.attributesOverride || false;
            var triggerEvent = args.triggerEvent || null;
            this.element.openPopup(anchor,
                                   position,
                                   x,
                                   y,
                                   isContextMenu,
                                   attributesOverride,
                                   triggerEvent)
        };
        
        
    }
).apply(Panel.prototype);

/**
 * Create an instance of a row object 
 *
 * @returns {Object} Row,  object which contains the koDom object of a
 * row (a.k.a hbox) element in the element property.
 */
module.exports.create = function panel_create($element = {}, options = {})
{
    return new Panel($element, options);
};