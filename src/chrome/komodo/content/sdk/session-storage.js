/**
 * @copyright (c) ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState
 */

const { Cc, Ci } = require("chrome");
const prefs = require("ko/prefs");
const ko = require("ko/windows").getMain().ko;

var global = window.global;

/**
 * simple-storage module which lets you store persistent data
 *
 * For storing preferences (user facing persistent data) use ko/prefs
 *
 * @module ko/simple-storage
 */
(function() {

    if ( ! ("sessionStorage" in global))
        global.sessionStorage = {};

    var storages = global.sessionStorage;

    /**
     * Get session data for the given name (will be created if it doesnt exist)
     *
     * Use the storage property to write and retrieve data.
     *
     * eg:
     * ```
     * var ss = require("ko/session-storage").get("foo");
     * ss.storage.foobar = "foo";
     * ```
     *
     * @param   {String} name
     *
     * @returns {Object} {storage: {}}
     */
    this.get = function(name)
    {
        if ( ! (name in storages))
            storages[name] = { storage: {} };

        return storages[name];
    };

    /**
     * Remove/purge all session data for the given name
     *
     * @param   {String} name
     *
     * @returns {Void}
     */
    this.remove = function(name)
    {
        if (name in storages)
            delete storages[name];
    };

}).apply(module.exports);