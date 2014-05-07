/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

(function delay_update_commands() {
    /**
     * Performance hack to delay command updates until after the Komodo UI is
     * fully started. This also collapses duplicate command updates in that time
     * (and there are quite a number of them), which further reduces startup
     * time.
     *
     * This reduces Komodo startup time (firstPaint) by 10-15%.
     */
    var pending_command_hash = {};
    var fallback_timeout = -1;
    var _log = require("ko/logging").getLogger("perf");
    //_log.setLevel(_log.LOG_DEBUG);

    var run_delayed_update_commands = function() {
        // #if BUILD_FLAVOUR == "dev"
        require("ko/benchmark").startTiming("run_delayed_update_commands");
        // #endif

        try {
            window.updateCommands = old_window_updateCommands;
            for (var commandsetname in pending_command_hash) {
                _log.debug("running delayed commandset update for '" + commandsetname + "'");
                window.updateCommands(commandsetname);
            }
        } catch (e) {
            _log.exception(e,"Error doing KomodoOnLoad:");
            throw e;
        }

        // #if BUILD_FLAVOUR == "dev"
        finally {
            require("ko/benchmark").endTiming("run_delayed_update_commands");
        }
        // #endif
    }

    // Add a fallback timer, in case komodo-ui-started does not fire.
    fallback_timeout = setTimeout(run_delayed_update_commands, 60000);

    // Wait till the Komodo UI is started.
    window.addEventListener("komodo-ui-started", function() {
        setTimeout(run_delayed_update_commands, 1000);
        clearTimeout(fallback_timeout);
    });

    // Temporarily replace updateCommands with our wrapper.
    var old_window_updateCommands = window.updateCommands;
    window.updateCommands = function(commandsetname) {
        pending_command_hash[commandsetname] = 1;
    }
})();

