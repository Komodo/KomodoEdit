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

    var Progress = function ()
    {
        var panel, message;

        var init = () =>
        {
            panel = require("ko/ui/panel").create({ attributes: {
                class: "dialog",
                style: "min-width: 250px",
                noautohide: true
            } });

            panel.addRow(
                require("ko/ui/row").create({ attributes: { class: "loader enabled", flex: 1 } }),
                { attributes: { align: "center", pack: "center" } }
            );

            panel.add(
                require("ko/ui/separator").create({ attributes: { class: "slim" } })
            );
            
            message = require("ko/ui/label").create("Loading ..");
            panel.addRow(
                message,
                { attributes: { align: "center", pack: "center" } }
            );

            panel.open();
        };

        this.message = (value) =>
        {
            message.value(value);
        };

        this.close = () =>
        {
            panel.remove();
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
        return new Progress();
    };

}).apply(module.exports);
