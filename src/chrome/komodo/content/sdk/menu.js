/**
 * @module menu
 */
(function(){

    const $ = require("ko/dom");
    const log = require("ko/logging").getLogger("sdk-menu");

    const XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";

    this.context = {
        editorContext: "#editorContextMenu"
    }

    /**
     * Register a new menu item
     * 
     * @param   {String|Object} label      Can also be the opts object, containing a label and command entry
     * @param   {Function} command
     * @param   {Object} opts   
     */
    this.register = (label, command, opts) =>
    {
        log.debug("Registering " + label);
        
        if ((typeof label) == "object")
        {
            opts = label;
        }
        else
        {
            opts.label = label;
            opts.command = command;
        }

        opts = _extend({
            image: "",
            command: function() {},
            classList: "",
            context: []
        }, opts);

        if ( ! ("label" in opts) && !(opts.separator))
        {
            throw new exceptionMissingProp("label");
        }

        if ( ! ("id" in opts))
        {
            opts.id = opts.label;
        }

        opts.id = opts.id.replace(/\W+/g, "");

        var context = _parseContext(opts.context);
        for (let i=0;i<context.length;i++)
        {
            _register(opts, context[i]);
        }
    };

    /**
     * Unregister a menu item
     * 
     * @param   {String} id  
     * @param   {Object} opts       used for context
     */
    this.unregister = (id, opts) =>
    {
        id = id.replace(/\W+/g, "");

        var context = _parseContext(opts.context);
        for (let i=0;i<context.length;i++)
        {
            let contextOpts = context[i];
            let _context = $(contextOpts.select);
            if ( ! _context || ! _context.length || _context.element().nodeName != "menupopup")
                throw new exceptionInvalidContext(contextOpts.select || "null");

            // TODO: this does not work.
            // $("#sdk_menuitem_" + _context.uniqueId() + id).element().remove() works.
            _context.find("sdk_menuitem_" + _context.uniqueId() + id).element().remove();
        }
    }

    var _register = (opts, contextOpts) =>
    {
        if ((typeof contextOpts) == "string")
        {
            contextOpts = {select: contextOpts};
        }

        var contexts = $(contextOpts.select);
        if ( ! contexts.length || contexts.element().nodeName != "menupopup")
            throw new exceptionInvalidContext();

        contexts.each(function()
        {
            let context = $(this);
            
            let id = "sdk_menuitem_" + context.uniqueId() + opts.id;
            context.find(id).remove();
    
            let menuitem = document.createElementNS(XUL_NS, !opts.separator ? 'menuitem' : 'menuseparator');
            menuitem.setAttribute("id", id);
            if (!opts.separator) {
                menuitem.setAttribute("label", opts.label);
                menuitem.setAttribute("image", opts.image);
                menuitem.setAttribute("class", opts.classList);
                menuitem.setAttribute("disabled", opts.disabled || false);
                menuitem.addEventListener("command", opts.command);
            }
            
            // Optionally set custom attributes
            try
            {
                if (opts.attributes)
                {
                    for (let k in opts.attributes)
                    {
                        if ( ! opts.attributes.hasOwnProperty(k)) continue;
                        menuitem.setAttribute(k, opts.attributes[k]);
                    }
                }
            } catch (e)
            {
                log.exception(e, "Setting attributes failed");
            }
            
            menuitem.classList.add("sdk-menuitem");
    
            menuitem.sdkOpts = opts;
    
            let sibling, appended;
            if (contextOpts.before || contextOpts.after)
            {
                sibling = context.find(contextOpts.before || contextOpts.after);
                if (sibling.length)
                {
                    sibling[contextOpts.before ? 'before' : 'after'](menuitem);
                    appended = true;
                }
            }
    
            if ( ! appended)
            {
                context.append(menuitem);
            }
    
            placeMenuEventListener(context);
        });
    }

    var _parseContext = (context) =>
    {
        if ( ! Array.isArray(context))
        {
            context = [context];
        }

        for (let i=0;i<context.length;i++)
        {
            if ((typeof context[i]) == "string")
            {
                context[i] = {select: context[i]};
            }
        }

        return context;
    }

    var placeMenuEventListener = (context) =>
    {
        if ("sdkMenuListener" in context)
        {
            return;
        }

        context.sdkMenuListener = true;

        context.on("popupshowing", (e) =>
        {
            context.find(".sdk-menuitem").each(function ()
            {
                if ( ! ("sdkOpts" in this)) return;
                var opts = this.sdkOpts;

                if (("isEnabled" in opts))
                {
                    if (! opts.isEnabled(e, context, this))
                    {
                        this.setAttribute("disabled", "true");
                    }
                    else
                    {
                        this.removeAttribute("disabled");
                    }
                }

                if (("isVisible" in opts))
                {
                    if (! opts.isVisible(e, context, this))
                    {
                        this.setAttribute("collapsed", "true");
                    }
                    else
                    {
                        this.removeAttribute("collapsed");
                    }
                }
            });
        });
    }

    /**
     * Exception thrown when the context is not valid
     */
    function exceptionInvalidContext(context)
    {
        this.message = "The context cannot be found or is not a menupopup";
    }
    this.exceptionInvalidContext = exceptionInvalidContext;

    /**
     * Exception thrown when a required property is missing
     */
    function exceptionMissingProp(prop)
    {
        this.message = "Menu registration failed due to missing " + prop + " property";
    }
    this.exceptionMissingProp = exceptionMissingProp;

    var _extend = () =>
    {
        var ob = {};
        for (let k in arguments)
        {
            let _ob = arguments[k];
            for (let _k in _ob)
            {
                if ( ! _ob.hasOwnProperty(_k)) continue;
                ob[_k] = _ob[_k];
            }
        };
        return ob;
    }

}).apply(module.exports);
