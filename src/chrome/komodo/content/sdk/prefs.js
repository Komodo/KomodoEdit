/**
 * @copyright (c) 2015 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState
 * @overview -
 */

const {Cc, Ci} = require("chrome");
const w = require("ko/windows").getMain();
const log = require("ko/logging").getLogger("ko/prefs");

log.setLevel(10);

const LEVEL_GLOBAL = 'global';
const LEVEL_PROJECT = 'project';
const LEVEL_FILE = 'file';

var storage = require("ko/session-storage").get("pref-catagories").storage

var PreferenceSet = function(prefset, level = LEVEL_GLOBAL)
{
    var cache = {};

    var init = () =>
    {
        /**
         * Wrap the Komodo global preferences (XPCOM) object.
         */
        for (let name of Object.keys(prefset.__proto__))
        {
            if (name == "QueryInterface")
                continue;
            if (name in this)
                continue;
            if (typeof(prefset[name]) == "function")
            {
                this[name] = prefset[name].bind(prefset);
            }
            else
            {
                // Wrap in a closure, so name (n) remains the same.
                ((n) =>
                {
                    Object.defineProperty(this, n,
                    {
                        get: function() { return prefset[n]; },
                        set: function(newValue) { prefset[n] = newValue; },
                    });
                })(name);
            }
        }
    };

    var cached = (method, name, fallback) =>
    {
        log.debug(`Calling ${method}(${name}, ${fallback})`);

        var baseMethod = `${method}Pref`.replace('PrefPref', '');

        if (baseMethod != method && fallback === undefined)
        {
            switch (method)
            {
                case "getString":
                    fallback = "";
                    break;
                case "getBoolean":
                    fallback = false;
                    break;
                case "getLong":
                    fallback = 0;
                    break;
            }
        }

        var result;
        if (name in cache)
        {
            log.debug("Using cache");
            result = cache[name];
        }
        else
        {
            log.debug("Calling koPref component");

            try
            {
                result = prefset[baseMethod](name);
            }
            catch(e)
            {
                result = null;
            }

            cache[name] = result;
        }

        if (result === null)
        {
            if (fallback === undefined)
                throw Error(`The preference '${name}' does not exist in '${level}'`);

            log.debug("Returning fallback");
            return fallback;
        }

        return result;
    };

    /**
     * Check if the preference exists (is defined)
     *
     * @function hasPref
     *
     * @param {String}      name     The preference name
     *
     * @returns {Boolean}
     */
    this.hasPref = (name) =>
    {
        if (name in cache && cache[name] !== null)
            return true;
        return prefset.hasPref.apply(prefset, arguments);
    };

    /**
     * Check if the preference exists (is defined) on the current scope (not the parent scopes)
     *
     * @function hasPrefHere
     *
     * @param {String}      name     The preference name
     *
     * @returns {Boolean}
     */
    // Handled by init logic

    /**
     * Get a string preference, defaults to an empty string
     *
     * @function getString
     *
     * @param {String}      name     The preference name
     * @param {String}      default  The default to return if the pref was not set
     *
     * @returns {String}
     */
    this.getString = cached.bind(this, "getString");

    this.getStringPref = cached.bind(this, "getStringPref");

    /**
     * Set a string preference
     *
     * @function setString
     *
     * @param {String}      name    The preference name
     * @param {String}      value   The preference value
     */
    // Handled by init logic

    /**
     * Get a boolean preference, defaults to false
     *
     * @function getBoolean
     *
     * @param {String}      name     The preference name
     * @param {Boolean}     default  The default to return if the pref was not set
     *
     * @returns {Boolean}
     */
    this.getBoolean = cached.bind(this, "getBoolean");

    this.getBooleanPref = cached.bind(this, "getBooleanPref");

    /**
     * Set a boolean preference
     *
     * @function setBoolean
     *
     * @param {String}      name    The preference name
     * @param {Boolean}     value   The preference value
     *
     * @returns {Boolean}
     */
    // Handled by init logic

    /**
     * Get a long (integer) preference, defaults to 0
     *
     * @function getLong
     *
     * @param {String}      name     The preference name
     * @param {Long}        default  The default to return if the pref was not set
     *
     * @returns {Long}
     */
    this.getLong = (name) => cached.bind(this, "getLong");

    this.getLongPref = cached.bind(this, "getLongPref");

    /**
     * Set a long (integer) preference
     *
     * @function setLong
     *
     * @param {String}      name    The preference name
     * @param {Long}        value   The preference value
     *
     * @returns {Long}
     */
    // Handled by init logic

    /**
     * Get a child prefset
     *
     * @function getPref
     *
     * @param {String}      name     The preference name
     *
     * @returns {prefset}
     */
    this.getPref = cached.bind(this, "getPref");

    /**
     * Set a prefset value
     *
     * @function setPref
     *
     * @param {String}      name    The preference name
     * @param {prefset}     value   The preference value
     *
     * @returns {void}
     */
    // Handled by init logic

    var observer =
    {
        observing: {},
        observe: function(subject, topic, data)
        {
            if (topic in cache)
            {
                delete cache[topic];
            }

            observer.observing[topic].forEach(function(callback)
            {
                callback(subject, topic, data);
            });
        }
    };

    /**
     * Handle change event for a pref
     *
     * @function onChange
     *
     * @param {String}      name     The preference name
     * @param {Function}    callback
     *
     * @returns {void}
     */
    this.onChange = function(pref, callback)
    {
        if ( ! (pref in observer.observing))
        {
            observer.observing[pref] = [];
            prefs.prefObserverService.addObserver(observer, pref, false);
        }

        observer.observing[pref].push(callback);
    };

    /**
     * Remove a callback handler for a pref change event
     *
     * @function removeOnChange
     *
     * @param {String}      name     The preference name
     * @param {Function}    callback 
     *
     * @returns {void}
     */
    this.removeOnChange = function(pref, callback)
    {
        if ( ! (pref in observer.observing)) return;

        observer.observing[pref].forEach(function(_callback, index)
        {
            if (callback == _callback)
            {
                observer.observing[pref].splice(index,1);

                if ( ! observer.observing[pref].length)
                {
                    delete observer.observing[pref];
                    prefs.prefObserverService.removeObserver(observer, pref, false);
                    return false;
                }
            }
        });
    };

    init();
};

/**
 * The prefs SDK allows you to access Komodo's preferences, it returns an
 * instance of PreferenceSet
 *
 * @module ko/prefs
 */
module.exports = new PreferenceSet(
    Cc["@activestate.com/koPrefService;1"].getService(Ci.koIPrefService).prefs
);

(function()
{
    /**
     * Return the current projects prefs
     * Falls back to global if there is no project open
     *
     * @function project
     *
     * @returns {PreferenceSet}
     */
    this.project = () =>
    {
        var prefs;
        if(w.ko.projects.manager.currentProject)
        {
            return new PreferenceSet(w.ko.projects.manager.currentProject.prefset, LEVEL_PROJECT);
        }
        else
        {
            return this;
        }
    };

    /**
     * Return the current files prefs
     * Falls back to project level if there is no file open
     * Then Falls back to global level if there is no project open
     *
     * @function file
     *
     * @returns {PreferenceSet}
     */
    this.file = function()
    {
        if(w.ko.views.manager.currentView)
        {
            return new PreferenceSet(w.ko.views.manager.currentView.koDoc.prefs, LEVEL_FILE);
        }
        else
        {
            return this.project();
        }
    };
        
    /**
     * Register a preference set to be displayed in the prefs window
     *
     * @param {String}      name    The preference name that will be displayed in the preferences window
     * @param {String}      path    The chrome path to your *.xul file
     * @param {String}      insertAfter     ID of the element to insert after
     */
    this.registerCatagory = function(name, path, insertAfter=null )
    {
        let id = name.replace(/\s/g,"_");
        let prefCatagoryStorage = storage;
        if ( ! prefCatagoryStorage.registered )
        {
            prefCatagoryStorage.registered = [];
            prefCatagoryStorage.catagories = [];
        }
        if ( prefCatagoryStorage.registered.indexOf(path) < 0)
        {
            prefCatagoryStorage.registered.push(path);
            prefCatagoryStorage.catagories.push({ name: name, path: path, id: id, insertAfter: insertAfter });
        }
    };
    
    this.getRegisteredCatagories = function()
    {
        return storage.catagories;
    };

}).apply(module.exports);