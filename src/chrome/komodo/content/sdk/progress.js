/**
 * @copyright (c) ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState
 * @overview -
 */

/**
 * Shows a small panel with an undetermined progress indicator, allows setting
 * of messages to indicate progress
 *
 * @module ko/progress
 */
(function()
{

    var Progress = function (opts = {})
    {
        var parent, message;

        var callbacks = { message: [], close: [] };

        opts.panel = opts.panel || false;

        var init = () =>
        {
            if (opts.panel)
            {
                parent = require("ko/ui/panel").create({ attributes: {
                    class: "dialog ui-progress-parent",
                    style: "min-width: 250px",
                    noautohide: true
                } });
            }
            else
            {
                parent = require("ko/ui/column").create({ attributes: {
                    class: "ui-progress-parent",
                    style: "min-width: 250px"
                } });
            }

            this.$element = parent.$element;
            this.element = parent.element;

            parent.addRow(
                require("ko/ui/row").create({ attributes: { class: "loader enabled", flex: 1 } }),
                { attributes: { align: "center", pack: "center" } }
            );

            parent.add(
                require("ko/ui/spacer").create({ attributes: { class: "slim" } })
            );
            
            message = require("ko/ui/label").create("Loading ..");
            parent.addRow(
                message,
                { attributes: { align: "center", pack: "center" } }
            );

            if (opts.panel)
            {
                parent.open();
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
     * @returns {Progress} Returns instance of progress, which holds the .message(value) and .close() methods
     */
    this.open = () =>
    {
        return new Progress({panel: true});
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
