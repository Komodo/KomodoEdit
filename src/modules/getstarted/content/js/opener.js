/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/. */
(function()
{

    var controller =
    {
        /**
         * Show the getting started dialog
         */
        do_cmd_viewGetStarted: function()
        {
            ko.windowManager.openDialog("chrome://getstarted/content/dialog.xul", "getStarted",
                                        "chrome,close=yes,centerscreen");
        },

        /**
         * Check whether command is supported
         *
         * @param   {String} command
         *
         * @returns {Bool}
         */
        supportsCommand: function(command)
        {
            return ("do_" + command) in this;
        },

        /**
         * Execute command
         *
         * @param   {String} command
         *
         * @returns {Mixed}
         */
        doCommand: function(command)
        {
            return this["do_" + command]();
        }
    };

    window.controllers.appendController(controller);

    // Show dialog on startup if preferred / unconfigured. We also want to
    // force showing of this dialog on every major.minor Komodo update.
    var koMajorMinor = ko.version.split(".").slice(0, 2).join(".");
    var prefName = 'show-getstarted-' + koMajorMinor;
    var hasPref = ko.prefs.hasPref(prefName);
    if (ko.prefs.getBoolean(prefName, false) || ! hasPref)
    {
        if ( ! hasPref)
        {
            ko.prefs.setBooleanPref(prefName, false);
        }

        window.addEventListener("komodo-ui-started", function() { ko.commands.doCommandAsync('cmd_viewGetStarted') });
    }

})();
