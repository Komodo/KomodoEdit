(function(){

    var $ = require("ko/dom");
    var _ = require("contrib/underscore");

    const XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";

    this.register = (label, command, opts) =>
    {
        if ((typeof label) == "object")
        {
            opts = label;
        }
        else
        {
            opts.label = label;
            opts.command = command;
        }

        opts = _.extend({
            toolbar: false,
            command: function() {},
            classList: "",
            context: []
        }, opts);

        if ( ! ("label" in opts))
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

    this.unregister = (id, context) =>
    {
        id = id.replace(/\W+/g, "");

        var context = _parseContext(opts.context);
        for (let i=0;i<context.length;i++)
        {
            let contextOpts = context[i];
            let _context = $(contextOpts.select);
            if ( ! context || ! context.length)
                throw new exceptionInvalidContext(contextOpts.select || "null");

            _context.parent().find("sdk_button_" + contextOpts.uniqueId() + opts.id).remove();
        }
    }

    var _register = (opts, contextOpts) =>
    {
        if ((typeof contextOpts) == "string")
        {
            contextOpts = {select: contextOpts, where: "after"};
        }

        var context = $(contextOpts.select);
        if ( ! context.length)
            throw new exceptionInvalidContext();

        var id = "sdk_button_" + context.uniqueId() + opts.id;
        context.parent().find(id).remove();

        var button = document.createElementNS(XUL_NS, 'button');
        button.setAttribute("id", id);
        button.setAttribute("label", opts.label);
        button.setAttribute("class", opts.classList);

        button.addEventListener("command", opts.command);
        button.classList.add("sdk-button");

        button.sdkOpts = opts;

        var sibling, appended;
        if (context.where == "before")
        {
            context.before(button);
        }
        else
        {
            context.after(button);
        }
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
                context[i] = {select: context[i], where: "after"};
            }
        }

        return context;
    }

    function exceptionInvalidContext(context)
    {
        this.message = "The context cannot be found";
    }
    this.exceptionInvalidContext = exceptionInvalidContext;

    function exceptionMissingProp(prop)
    {
        this.message = "Button registration failed due to missing " + prop + " property";
    }
    this.exceptionMissingProp = exceptionMissingProp;

}).apply(module.exports);
