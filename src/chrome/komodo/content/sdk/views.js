/**
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState
 */

/**
 * Easily interface with Komodo's views (tabs/editors)
 *
 * @module ko/views
 */
(function()
{

    var w = require("ko/windows").getMain();
    var ko = w.ko;

    /**
     * Access the view manager (see ko.views.manager)
     */
    this.manager = ko.views.manager;

    /**
     * Access the current (active) view (see ko.views.manager.currentView)
     *
     * Returns an object containing:
     *
     * get() - returns a propery from the currentView object, possible properties:
     *
     *  - scintilla
     *  - scimoz
     *  - koDoc
     *  - file
     *  - filePath
     *  - prefs
     *  - language
     *  - type
     *
     * For example:
     *
     * ```
     * require("ko/views").current().get("language")
     * ```
     *
     * gets the language for the current view
     *
     * @returns {Object}
     */
    this.current = function()
    {
        var view = ko.views.manager.currentView;

        /**
         * Get a property
         *
         * @returns {Mixed}
         */
        var get = function()
        {
            var result = view;

            if (!arguments.length) return view;

            for (let x=0; x<arguments.length;x++)
            {
                if ( ! result || ! (arguments[x] in result))
                {
                    return false;
                }

                result = result[arguments[x]];
            }

            return result;
        }

        return {
            get: get,

            uid: get("uid"),
            scintilla: get("scintilla"),
            scimoz: get("scimoz"),
            koDoc: get("koDoc"),
            file: get("koDoc", "file"),
            filePath: get("koDoc", "file", "path"),
            url: get("koDoc", "file", "URI"),
            prefs: get("koDoc", "prefs"),
            language: get("koDoc", "language"),
            title: get("title"),
            basename: get("koDoc","file","baseName"),
            dirname: get("koDoc","file","dirName"),

            type: view ? view.getAttribute("type") : false
        }
    }

    /**
     * Retrieve all views
     *
     * @function all
     *
     * @returns {Array}
     */
    this.all = this.manager.getAllViews.bind(this.manager);

    /**
     * Retrieve all editor views
     *
     * @function editors
     *
     * @returns {Array}
     */
    this.editors = this.manager.getAllViews.bind(this.manager, "editor");

    /**
     * Split the view
     *
     * @function split
     */
    this.split = ko.commands.doCommandAsync.bind(ko.commands, 'cmd_splittab')

    /**
     * Rotate the split view
     *
     * @function rotate
     */
    this.rotate = ko.commands.doCommandAsync.bind(ko.commands, 'cmd_rotateSplitter')
    
   /**
     * Get left splitview panel
     *
     * @function getLeftSplit
     */
    this.getLeftSplit = () =>
    {
        return require("ko/dom")("#view-1").element();
    };
    
    /**
     * Get right splitview panel
     *
     * @function getRightSplit
     */
    this.getRightSplit = () =>
    {
        return require("ko/dom")("#view-2").element();
    };
    /**
     * Get left file view
     *
     * @function getLeftView
     */
    
    this.getLeftView = () =>
    {
        return this.getLeftSplit().currentView;
    };
    
    /**
     * Get right file view
     *
     * @function getRightView
     */
    this.getRightView = () =>
    {
        return this.getRightSplit().currentView;
    };
    
    /**
     * Is Komodo in splitview mode?
     *
     * @function isSplit
     */
    this.isSplit = () =>
    {
        return require("ko/dom")("#view-2").visible();
    };

}).apply(module.exports);
