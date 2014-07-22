/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/. */

(function() {

    const {Cc, Ci, Cu}  = require("chrome");
    const $             = require("ko/dom");
    const prefs         = ko.prefs;
    const keyManager    = ko.keybindings.manager;

    const log           = require("ko/logging").getLogger("ko-keybindings");
    //log.setLevel(require("ko/logging").LOG_DEBUG);

    var local = {registered: {}};

    /**
     * Init, register main command controller
     */
    var init = () =>
    {
        window.controllers.appendController(controller);
    }

    /**
     * Virtual command controller, no reason to force consumers through this
     * needless complexity
     */
    var controller = {
        // Overloading
        supportsCommand: function(command)
        {
            return (command in local.registered);
        },

        isCommandEnabled: function(command)
        {
            if ( ! ("isEnabled" in local.registered[command].opts)) return true;
            return local.registered[command].opts.isEnabled();
        },

        doCommand: function(command)
        {
            return local.registered[command].command();
        }
    };

    /**
     * Add a new keybind
     *
     * @param {string}          commandName
     * @param {string|array}    keybind ["Ctrl+U", "A"] | "Ctrl+C"
     * @param {bool} force      Whether to override any existing keybinds
     */
    this.addKeybind = (commandName, keybind, force) =>
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

        keyManager.saveCurrentConfiguration();
    }

    /**
     * Remove a keybind
     *
     * @param {string} commandName
     */
    this.removeKeybind = (commandName) =>
    {
        if (commandName.indexOf("cmd") !== 0)
            commandName = "cmd_" + commandName;
            
        var label = keyManager.command2keylabel(commandName);

        if ( ! label || ! label.length) return;

        keyManager.clearSequence(commandName, label);

        keyManager.saveCurrentConfiguration();
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

    /**
     * Register a "command"
     *
     * A command is a function which can be bound to a key
     *
     * @param {string}      commandName
     * @param {function}    command
     * @param {object}      opts         {defaultBind: "Ctrl+U", isEnabled: fn, forceBind: false}
     *
     * Can throw:
     *  - keybindings.exceptionInvalidCommandName
     *  - keybindings.exceptionAlreadyUsed
     */
    this.register = (commandName, command, opts = {}) =>
    {
        if (commandName.indexOf("cmd") !== 0)
            commandName = "cmd_" + commandName;

        if ( ! commandName.match(/^[a-zA-Z0-9_\-]+$/))
            throw new this.exceptionInvalidCommandName;

        if (document.getElementById(commandName))
            throw new this.exceptionAlreadyUsed;

        var commandNode = $("<command/>");
        commandNode.attr({
            id: commandName,
            key: "key_" + commandName,
            onCommand: "ko.commands.doCommandAsync('"+commandName+"', event)",
            desc: opts.label || commandName
        });
        $("#allcommands").append(commandNode);

        log.debug(("defaultBind" in opts));
        if (("defaultBind" in opts) && opts.defaultBind)
            this.addKeybind(commandName, opts.defaultBind, opts.forceBind);

        local.registered[commandName] = {
            command: command,
            opts: opts
        };
    }

    /**
     * Unregister the given command
     *
     * @param {string}      commandName
     */
    this.unRegister = (commandName) =>
    {
        if (commandName.indexOf("cmd") !== 0)
            commandName = "cmd_" + commandName;

        if ( ! (commandName in local.registered))
        {
            log.warn("Trying to unregister nonexistant command: " + commandName);
            return;
        }

        var opts = local.registered[commandName].opts;
        var label = local.registered[commandName].opts.label || commandName;
        this.removeKeybind(commandName,label);
        
        $("#"+commandName).remove();
        delete local.registered[commandName];
    }

    function exceptionInvalidCommandName(commandName)
    {
        this.message = "The command '"+commandName+"' is not formed properly (^[a-zA-Z0-9_\-]+$)";
    }
    this.exceptionInvalidCommandName = exceptionInvalidCommandName;

    function exceptionAlreadyUsed(commandName)
    {
        this.message = "The command '"+commandName+"' is already in use";
    }
    this.exceptionAlreadyUsed = exceptionAlreadyUsed;

    init();

}).apply(module.exports);
