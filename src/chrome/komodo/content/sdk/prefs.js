/**
 * @copyright (c) 2015 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState
 * @overview -
 */

const {Cc, Ci} = require("chrome");
const w = require("ko/windows").getMain();

/**
 * Wrap the Komodo global preferences (XPCOM) object.
 */

/**
 * The prefs SDK allows you to access Komodo's preferences
 *
 * @module ko/prefs
 */
var exports = module.exports;
var prefs = Cc["@activestate.com/koPrefService;1"].
                getService(Ci.koIPrefService).prefs;
for (var name of Object.keys(prefs.__proto__)) {
    if (name == "QueryInterface") {
        continue;
    }
    if (typeof(prefs[name]) == "function") {
        exports[name] = prefs[name].bind(prefs);
    } else {
        // Wrap in a closure, so name (n) remains the same.
        (function(n) {
            Object.defineProperty(exports, n, {
                get: function() { return prefs[n]; },
                set: function(newValue) { prefs[n] = newValue; },
            });
        })(name);
    }
}

var observer =
{
    observing: {},
    observe: function(subject, topic, data)
    {
        observer.observing[topic].forEach(function(callback)
        {
            callback(subject, topic, data);
        });
    }
}

exports.onChange = function(pref, callback)
{
    if ( ! (pref in observer.observing))
    {
        observer.observing[pref] = [];
        prefs.prefObserverService.addObserver(observer, pref, false);
    }

    observer.observing[pref].push(callback);
}

exports.removeOnChange = function(pref, callback)
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
}

/**
 * Return the current projects prefs
 * Falls back to global if there is no project open
 */
exports.project = function()
{
    var prefs;
    if(w.ko.projects.manager.currentProject)
    {
        return w.ko.projects.manager.currentProject.prefset;
    }
    else
    {
        return exports;
    }
};

/**
 * Return the current files prefs
 * Falls back to project level if there is no file open
 * Then Falls back to global level if there is no project open
 */
exports.file = function()
{
    if(ko.views.manager.currentView)
    {
        return w.ko.views.manager.currentView.koDoc.prefs;
    }
    else
    {
        return exports.project();
    }
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

/**
 * Check if the preference exists (is defined) on the current scope (not the parent scopes)
 *
 * @function hasPrefHere
 *
 * @param {String}      name     The preference name
 *
 * @returns {Boolean}
 */

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

/**
 * Set a string preference
 *
 * @function setString
 *
 * @param {String}      name    The preference name
 * @param {String}      value   The preference value
 */


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

