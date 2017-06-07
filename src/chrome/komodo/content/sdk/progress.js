/**
 * @copyright (c) ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState
 * @overview -
 */

/**
 * Shows a small panel with a progress indicator, allows setting
 * of messages to indicate progress
 *
 * @module ko/progress
 */
(function()
{

    var Progress = function (opts = {})
    {
        var parent, message, loader, spacer;

        var callbacks = { message: [], close: [] };

        opts.panel = opts.panel || false;

        var init = () =>
        {
            if (opts.panel)
            {
                parent = require("ko/ui/panel").create({ attributes: {
                    class: "dialog ui-progress-parent",
                    noautohide: true
                } });
            }
            else
            {
                parent = require("ko/ui/column").create({ attributes: {
                    class: "ui-progress-parent"
                } });
            }

            this.$element = parent.$element;
            this.element = parent.element;

            loader = require("ko/ui/row").create({ attributes: { class: "loader enabled", determined: opts.determined } });
            if ( ! opts.determined)
                loader.attr("flex", 1);

            var row = parent.addRow(
                loader,
                { attributes: { align: "start", pack: "center" } }
            );
            
            if (opts.determined)
                spacer = row.addRow({ flex: 100 });

            parent.add(
                require("ko/ui/spacer").create({ attributes: { class: "slim" } })
            );
            
            message = require("ko/ui/label").create("Loading ..", { crop: "center" });
            parent.addRow(
                message,
                { attributes: { align: "center", pack: "center" } }
            );

            if (opts.panel)
            {
                parent.open();
                new require("ko/windows/draggable")(parent.element);
            }
        };

        this.on = (type, callback) =>
        {
            if ( ! (type in callbacks))
                return;
            
            callbacks[type].push(callback);
        };

        this.off = (type, callback) =>
        {
            if ( ! (type in callbacks))
                return;

            callbacks[type] = callbacks[type].filter((v) => v != callback);
        };

        this.percentage = (value) =>
        {
            loader.attr("flex", value);
            spacer.attr("flex", 100 - value);
        };

        this.message = (value) =>
        {
            message.value(value);

            for (let callback of callbacks.message)
            {
                callback(value);
            }
        };

        this.close = (force = false) =>
        {
            var stop = false;

            for (let callback of callbacks.close)
            {
                if (callback() === false)
                {
                    stop = true;
                }
            }

            if ( ! stop || force)
                parent.$element.remove();
        };

        init();
    };


    /**
     * Open a new progress panel
     *
     * @param {bool} determined     whether this progress indicator is determined or undetermined (spinner or load progress)
     *
     * @returns {Progress} Returns instance of progress, which holds the .message(value) and .close() methods
     */
    this.open = (determined = false) =>
    {
        return new Progress({panel: true, determined: determined});
    };
    
    /**
     * Get a progress element, which can be inserted into the DOM however wanted
     *
     * @returns {Progress} Returns instance of progress, which holds the .message(value) and .close() methods
     */
    this.get = (callback) =>
    {
        return new Progress({panel: false});
    };

}).apply(module.exports);
