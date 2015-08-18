/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * @module keybindings
 */
(function() {

    const _ko            = require("ko/windows").getMain().ko;
    const {Cc, Ci, Cu}  = require("chrome");
    const $             = require("ko/dom");
    const prefs         = _ko.prefs;
    const keyManager    = _ko.keybindings.manager;

    const log           = require("ko/logging").getLogger("ko-keybindings");
    //log.setLevel(require("ko/logging").LOG_DEBUG);

    var saveKeyBindings = () =>
    {
        keyManager.saveCurrentConfiguration();
        keyManager._saveKnownConfigs();
        keyManager.loadConfiguration(keyManager.currentConfiguration, true);
        _ko.toolbox2.applyKeybindings();
    };

    /**
     * Add a new keybind
     *
     * @param {string}          commandName
     * @param {string|array}    keybind ["Ctrl+U", "A"] | "Ctrl+C"
     * @param {bool} force      Whether to override any existing keybinds
     */
    this.register = (commandName, keybind, force) =>
    {
        if (commandName.indexOf("cmd") !== 0)
            commandName = "cmd_" + commandName;
            
        if (Object.prototype.toString.call(keybind) !== '[object Array]')
        {
            keybind = keybind.split(", ");
        }
        
        if (this.usedBy(keybind).length)
        {
            log.debug("keybind already in use" + (JSON.stringify(keybind)));
            if ( ! force) return;
        }

        keyManager.assignKey(commandName, keybind);
        keyManager.makeKeyActive(commandName, keybind);

        saveKeyBindings();
    }

    /**
     * Remove a keybind
     *
     * Todo: this should act on the keybind, not the command
     *
     * @param {string} commandName
     */
    this.unregister = (commandName) =>
    {
        if (commandName.indexOf("cmd") !== 0)
            commandName = "cmd_" + commandName;
            
        var label = keyManager.command2keylabel(commandName);

        if ( ! label || ! label.length) return;

        keyManager.clearSequence(commandName, label);

        saveKeyBindings();
    }

    /**
     * Retrieve string representation of keybind for command
     *
     * @param {string} commandName
     *
     * @returns {string}
     */
    this.getKeybindFromCommand = (commandName) =>
    {
        return keyManager.command2keylabel(commandName);
    }

    /**
     * Check what the given keybind is used by
     *
     * @param {string|array} keybind ["Ctrl+U", "A"] | "Ctrl+C"
     *
     * @returns {array}
     */
    this.usedBy = (keybind) =>
    {
        if ( ! (keybind instanceof Array))
        {
            keybind = keybind.split(", ");
        }

        return keyManager.usedBy(keybind);
    }

}).apply(module.exports);
