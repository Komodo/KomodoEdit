/**
 * @copyright (c) 2015 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @overview Row sub module for the ko/ui SDK
 *
 */

/**
 * "declaration" of the Row class.  Uses the init() function as a constructor
 */
function Menulist($element = {}, options = {}) { this.init($element, options); }

(function()
    {
        var $ = require("ko/dom");
        var log = require("ko/logging").getLogger("ko-menulist");
        this.type = "menulist";
        
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
            this.element = this.$elem.element.bind(this.$elem); // Actual DOM object
        };
        
        /**
         * Add menu item/s to menulist.  Wraps menuitems in a <menupopup>
         *
         * @argument {Array} menuitems  An array of menu item pairs to be added
         *     to the menulist
         *     [
                    [
                        itemName, "onCommand function"
                    ],
                    [
                        itemName, "onCommand function"
                    ],
               ]
         */
        this.addMenuitems = function menulist_addMenuitems(menuitems)
        {
            for( var i  in menuitems)
            {
                // must wrap menu items in a <menupopup> element inside the
                // <menulist>
                var $menupop = {};
                if( this.$elem.children().length == 0 )
                {
                    $menupop = $($.create("menupopup").toString());
                    this.$elem.append($menupop);
                }
                else if ( this.$elem.children() &&
                          this.$elem.children().element() &&
                          this.$elem.children().element().nodeName == "menupopup")
                {
                    $menupop = this.$elem.children()
                }
                else
                {
                    log.error("Mandatory <menupopup> element is missing and could " +
                              "not be created.  Make sure your menulist has no " +
                              "other elements as it's immediate child");
                    return;    
                }
                var menuitem = menuitems[i];
                var $menuitem = $($.create("menuitem",
                                           {
                                                label:menuitem[0],
                                                id: menuitem[0],
                                                oncommand: menuitem[1]
                                            }).toString());
                
                $menupop.append($menuitem);
            }
        }
    }
).apply(Menulist.prototype);

/**
 * Create an instance of a Menulist object 
 *
 * @returns {Object} Menulist,  object which contains the koDom object
 */
module.exports.create = function menulist_create($element = {}, options = {})
{
    return new Menulist($element, options);
}
