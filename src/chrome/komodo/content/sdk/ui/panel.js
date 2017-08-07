/**
 * @copyright (c) 2016 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author CareyH
 * @overview Page sub module for the wizard SDK module
 *
 */

var parent = require("./container");
var Module = Object.assign({}, parent); 
var _window = require("ko/windows").getMain();
var _ = require("contrib/underscore");
module.exports = Module;

// Main module (module.exports)
(function() {
    
    this.Model = Object.assign({}, this.Model);
    
    (function() {
        
        this.name = "panel";
        
        this.init = this.initWithElement;

        /**
         * Show the panel.
         *
         * @param {object} args, options object can contain the following:
         *    Defaults to opening in the middle of the Komodo main window
         *    {
         *        anchor : dom object to anchor to,
         *        position:   "before_start, before_end, after_start, after_end, start_before, start_after, end_before, end_after, overlap, and after_pointer",
         *        x : number,
         *        y : number,
         *        isContextMenu : bool,
         *        attributes : bool,
         *        triggerEvent : event)
         *    }
         *    ref: https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/Method/openPopup
         * 
         */
        this.open = function panel_open(args)
        {
            if ( ! args)
                args = {};
                
            args = _.extend(this.options, args);
                
            var anchor =  args.anchor === undefined ? _window.document.documentElement : args.anchor;
            var parent = anchor || _window.document.documentElement;
            
            if( ! this.element.parentNode || ! this.element.parentNode.parentNode)
            {
                parent.ownerDocument.documentElement.appendChild(this.element);
            }
            
            var position = args.position || null;
            var x = args.x || 0;
            var y = args.y || 0;
            var isContextMenu = args.isContextMenu || false;
            var panelElement = this.element;

            if (anchor)
                panelElement.openPopup(anchor,
                                        position,
                                        x,
                                        y,
                                        isContextMenu);
            else
                panelElement.openPopupAtScreen(x, y, isContextMenu);
            
            var center = function()
            {
                if ( ! panelElement || ! panelElement.moveTo)
                    return;

                var x, y;
                if (anchor && ! args.x && ! args.y )
                {
                    x = anchor.boxObject.screenX + ((anchor.boxObject.width/2) - (panelElement.boxObject.width/2));
                    y = anchor.boxObject.screenY + ((anchor.boxObject.height/2) - (panelElement.boxObject.height/2));
                }
                else if (anchor && args.x && args.y)
                {
                    x = anchor.boxObject.screenX + args.x;
                    y = anchor.boxObject.screenY + args.y;
                }
                else
                {
                    x = args.x;
                    y = args.y;
                }

                if (args && args.align == "bottom")
                {
                    y -= panelElement.boxObject.height;
                }
                
                panelElement.moveTo(x,y);
            };
            
            // Yay XUL
            center();
            panelElement.addEventListener("popupshowing", center);
            panelElement.addEventListener("popupshown", center);
            _window.setTimeout(center, 100);
        };
        
        /**
         * Close the popup.  This does not delete the panel, it just hides it.
         *
         */
        this.close = function panel_close()
        {
            this.element.hidePopup();
        }
        
        /**
         * Remove the panel
         *
         */
        this.remove = function panel_remove()
        {
            this.element.remove();
        }
        
    }).apply(this.Model); 
    
}).apply(Module);
