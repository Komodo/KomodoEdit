/**
 * @copyright (c) 2015 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState
 * @overview -
 */

/**
 * An interface for the Komodo keybindings
 *
 * @module ko/keybindings
 */
(function() {

    const _ko            = require("ko/windows").getMain().ko;
    const {Cc, Ci, Cu}  = require("chrome");
    const $             = require("ko/dom");
    const prefs         = Cc["@activestate.com/koPrefService;1"].getService(Ci.koIPrefService).prefs;
    const keyManager    = _ko.keybindings.manager;
    const keybindingService =  Cc['@activestate.com/koKeybindingSchemeService;1'].getService();

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
        if ( ! Array.isArray(keybind) )
        {
            keybind = keybind.split(", ");
        }

        return keyManager.usedBy(keybind);
    }
    
    /**
     * Get the current key binding configuration
     *
     * @returns {String} name of the current keybinding configuration
     */
    this.getCurrentConfig = () =>
    {
        if(prefs.hasPref("keybinding-scheme"))
        {
            return prefs.getStringPref("keybinding-scheme");
        }
    }
    
    /**
     * Get the current key binding configuration
     *
     * @returns {Array} An array of all available keybinding sets
     */
    this.getConfigs = () =>
    {
        var schemes = new Array();
        keybindingService.getSchemeNames(schemes, new Object());
        return schemes.value;
    }
    
    
    

}).apply(module.exports);
