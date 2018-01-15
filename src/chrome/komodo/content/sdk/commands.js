/**
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState
 */

/**
 * The commands SDK allows you to register your own commands. This will allow
 * users to connect keybindings to it.
 *
 * @module ko/commands
 */
(function() {

    const {Cc, Ci, Cu}  = require("chrome");
    const $             = require("ko/dom");
    const prefs         = ko.prefs;
    const _window       = require("ko/windows").getMain();

    const log           = require("ko/logging").getLogger("ko-commands");
    //log.setLevel(require("ko/logging").LOG_DEBUG);

    var local = {registered: {}};

    /**
     * Init, register main command controller
     */
    var init = () =>
    {
        _window.controllers.appendController(controller);
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
     * Register a "command"
     *
     * A command is a function which can be bound to a key
     *
     * @param {string}      commandName     Name of the command
     * @param {function}    command         The callback
     * @param {object}      opts            label, defaultBind, forceBind
     *
     * @example
     * opts = {
     *      label:"",
     *      defaultBind:"CTRL+META+B", 
     *      forceBind:boolean, // override any existing bindings
     *   }
     *
     * @throws keybindings.exceptionInvalidCommandName
     * @throws keybindings.exceptionAlreadyUsed
     *  
     *
     */
    this.register = (commandName, command, opts = {}) =>
    {
        if (commandName.indexOf("cmd") !== 0)
            commandName = "cmd_" + commandName;

        if ( ! commandName.match(/^[a-zA-Z0-9_\-]+$/))
            throw new this.exceptionInvalidCommandName;

        if (document.getElementById(commandName))
            throw new this.exceptionAlreadyUsed;

        var commandNode = $("<command/>", _window);
        commandNode.attr({
            id: commandName,
            key: "key_" + commandName,
            oncommand: "ko.commands.doCommandAsync('"+commandName+"', event)",
            desc: opts.label || commandName
        });
        $("#allcommands", _window).append(commandNode);

        log.debug(("defaultBind" in opts));
        if (("defaultBind" in opts) && opts.defaultBind)
        {
            var keybinds = require("ko/keybindings");
            keybinds.register(commandName, opts.defaultBind, opts.forceBind);
        }

        local.registered[commandName] = {
            command: command,
            opts: opts
        };
    }

    /**
     * Unregister the given command
     *
     * @param {string}      commandName     Name of the Command
     */
    this.unregister = (commandName) =>
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

        var keybinds = require("ko/keybindings");
        keybinds.unregister(commandName,label);

        $("#"+commandName, _window).remove();
        delete local.registered[commandName];
    }

    /**
     * Exception that occurs when an invalid command name was given
     */
    function exceptionInvalidCommandName(commandName)
    {
        this.message = "The command '"+commandName+"' is not formed properly (^[a-zA-Z0-9_\-]+$)";
    }
    this.exceptionInvalidCommandName = exceptionInvalidCommandName;

    /**
     * Exception that occurs when the given command name is already being used
     */
    function exceptionAlreadyUsed(commandName)
    {
        this.message = "The command '"+commandName+"' is already in use";
    }
    this.exceptionAlreadyUsed = exceptionAlreadyUsed;

    init();

}).apply(module.exports);
