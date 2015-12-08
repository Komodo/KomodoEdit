
// Test common and somewhat tricky nuances of YUI.

YAHOO = {};
YAHOO.widget = {};


/**************************/
/*  Test YAHOO.extend()   */
/**************************/

    /**
     * The default node presentation.  The first parameter should be
     * either a string that will be used as the node's label, or an object
     * that has a string propery called label.  By default, the clicking the
     * label will toggle the expanded/collapsed state of the node.  By
     * changing the href property of the instance, this behavior can be
     * changed so that the label will go to the specified href.
     * @namespace YAHOO.widget
     * @class TextNode
     * @extends YAHOO.widget.Node
     * @constructor
     * @param oData {object} a string or object containing the data that will
     * be used to render this node
     * @param oParent {YAHOO.widget.Node} this node's parent node
     * @param expanded {boolean} the initial expanded/collapsed state
     */
    YAHOO.widget.TextNode = function(oData, oParent, expanded) {
    
        if (oData) { 
            this.init(oData, oParent, expanded);
            this.setUpLabel(oData);
        }
    
    };
    
    YAHOO.extend(YAHOO.widget.TextNode, YAHOO.widget.Node, {
        
        labelStyle: "ygtvlabel",
    
        labelElId: null,
    
        textNodeParentChange: function() {
            if (this.tree && !this.tree.hasEvent("labelClick")) {
                this.tree.createEvent("labelClick", this.tree);
            }
        },
    
        label: null
    });
    

/*********************************/
/*  Test an anonymous function   */
/*********************************/

    (function() {
    
    var Dom = YAHOO.util.Dom,
        Event = YAHOO.util.Event,
        CustomEvent = YAHOO.util.CustomEvent,
        Lang = YAHOO.lang;
    
    
    /**
    * The Menu class creates a container that holds a vertical list representing 
    * a set of options or commands.  Menu is the base class for all 
    * menu containers. 
    * @param {String} p_oElement String specifying the id attribute of the 
    * <code>&#60;div&#62;</code> element of the menu.
    * @param {String} p_oElement String specifying the id attribute of the 
    * <code>&#60;select&#62;</code> element to be used as the data source 
    * for the menu.
    * @param {<a href="http://www.w3.org/TR/2000/WD-DOM-Level-1-20000929/
    * level-one-html.html#ID-22445964">HTMLDivElement</a>} p_oElement Object 
    * specifying the <code>&#60;div&#62;</code> element of the menu.
    * @param {<a href="http://www.w3.org/TR/2000/WD-DOM-Level-1-20000929/
    * level-one-html.html#ID-94282980">HTMLSelectElement</a>} p_oElement 
    * Object specifying the <code>&#60;select&#62;</code> element to be used as 
    * the data source for the menu.
    * @param {Object} p_oConfig Optional. Object literal specifying the 
    * configuration for the menu. See configuration class documentation for 
    * more details.
    * @namespace YAHOO.widget
    * @class Menu
    * @constructor
    * @extends YAHOO.widget.Overlay
    */
    YAHOO.widget.Menu = function(p_oElement, p_oConfig) {
    
        if(p_oConfig) {
            this.parent = p_oConfig.parent;
            this.lazyLoad = p_oConfig.lazyLoad || p_oConfig.lazyload;
            this.itemData = p_oConfig.itemData || p_oConfig.itemdata;
        }
    
    
        YAHOO.widget.Menu.superclass.constructor.call(
            this, 
            p_oElement, 
            p_oConfig
        );
    
    };
    })();
    
    
/**************************************************/
/*  Test removal of <a href> tags for citdl type  */
/**************************************************/
    
    /**
    * Creates a list of options or commands which are made visible in response to 
    * an HTML element's "contextmenu" event ("mousedown" for Opera).
    *
    * @param {String} p_oElement String specifying the id attribute of the 
    * <code>&#60;div&#62;</code> element of the context menu.
    * @param {String} p_oElement String specifying the id attribute of the 
    * <code>&#60;select&#62;</code> element to be used as the data source for the 
    * context menu.
    * @param {<a href="http://www.w3.org/TR/2000/WD-DOM-Level-1-20000929/level-one-
    * html.html#ID-22445964">HTMLDivElement</a>} p_oElement Object specifying the 
    * <code>&#60;div&#62;</code> element of the context menu.
    * @param {<a href="http://www.w3.org/TR/2000/WD-DOM-Level-1-20000929/level-one-
    * html.html#ID-94282980">HTMLSelectElement</a>} p_oElement Object specifying 
    * the <code>&#60;select&#62;</code> element to be used as the data source for 
    * the context menu.
    * @param {Object} p_oConfig Optional. Object literal specifying the 
    * configuration for the context menu. See configuration class documentation 
    * for more details.
    * @class ContextMenu
    * @constructor
    * @extends YAHOO.widget.Menu
    * @namespace YAHOO.widget
    */
    YAHOO.widget.ContextMenu = function(p_oElement, p_oConfig) {
        YAHOO.widget.ContextMenu.superclass.constructor.call(
                this, 
                p_oElement,
                p_oConfig
            );
    };
    
    /**
    * Constant representing the name of the ContextMenu's events
    * @property YAHOO.widget.ContextMenu._EVENT_TYPES
    * @private
    * @final
    * @type Object
    */
    YAHOO.widget.ContextMenu._EVENT_TYPES = {
        "TRIGGER_CONTEXT_MENU": "triggerContextMenu",
        "CONTEXT_MENU": (
                            (YAHOO.widget.Module.prototype.browser == "opera" ? 
                                "mousedown" : "contextmenu")
                        ),
        "CLICK": "click"
    };
    
    /**
    * Constant representing the ContextMenu's configuration properties
    * @property YAHOO.widget.ContextMenu._DEFAULT_CONFIG
    * @private
    * @final
    * @type Object
    */
    YAHOO.widget.ContextMenu._DEFAULT_CONFIG = {
        "TRIGGER": { 
            key: "trigger" 
        }
    };
    
    
    YAHOO.lang.extend(YAHOO.widget.ContextMenu, YAHOO.widget.Menu, {
    
    // Private properties
    
    /**
    * @property _oTrigger
    * @description Object reference to the current value of the "trigger" 
    * configuration property.
    * @default null
    * @private
    * @type String|<a href="http://www.w3.org/TR/2000/WD-DOM-Level-1-20000929/leve
    * l-one-html.html#ID-58190037">HTMLElement</a>|Array
    */
    _oTrigger: null,
    
    
    /**
    * @property _bCancelled
    * @description Boolean indicating if the display of the context menu should 
    * be cancelled.
    * @default false
    * @private
    * @type Boolean
    */
    _bCancelled: false
    });
