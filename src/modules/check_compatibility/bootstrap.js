// Copyright © 2009-2011 Kris Maglione <maglione.k@gmail.com>
//
// This work is licensed for reuse under an MIT license. Details are
// given in the LICENSE file included with this file.
"use strict";

const { classes: Cc, interfaces: Ci, utils: Cu, results: Cr } = Components;

const PREF         = "extensions.checkCompatibility";
const PREF_NIGHTLY = "nightly";

function module(uri) Cu.import(uri, {});

const { AddonManager } = module("resource://gre/modules/AddonManager.jsm");
const { Services }     = module("resource://gre/modules/Services.jsm");
const { XPCOMUtils }   = module("resource://gre/modules/XPCOMUtils.jsm");

let listener = {
    get version() Services.appinfo.version.replace(/^([^\.]+\.[0-9]+[a-z]*).*/i, "$1"),

    init: function init(reason) {
        let self = this;
        function init() {
            prefs.defaults.set(PREF, false);
            prefs.branch.addObserver(PREF, self, false);
            self.observe(null, null, PREF);
        }

        let appVersion = Services.appinfo.version;
        if (reason != APP_STARTUP || appVersion == prefs.private.get("app-version"))
            init();
        else
            AddonManager.getAddonsByTypes(null, function (addons) {
                function count() addons.reduce(function (acc, a) acc + (a.appDisabled || a.isActive), 0);

                let startCount = count();
                init();
                if (startCount != count())
                    Cc["@mozilla.org/toolkit/app-startup;1"].getService(Ci.nsIAppStartup)
                        .quit(Ci.nsIAppStartup.eAttemptQuit | Ci.nsIAppStartup.eRestart);
            });

        prefs.private.set("app-version", appVersion);
    },

    cleanup: function cleanup() {
        prefs.branch.removeObserver(PREF, this, false);
        prefs.check.set(this.version, prefs.saved.get(this.version));
        prefs.check.set(PREF_NIGHTLY, prefs.saved.get(PREF_NIGHTLY));

        for each (let name in prefs.saved.getNames())
            prefs.saved.reset(name);
    },

    install: function install() {
        prefs.saved.set(PREF, prefs.get(PREF));
    },

    uninstall: function uninstall() {
        prefs.set(PREF, prefs.saved.get(PREF));
    },

    QueryInterface: XPCOMUtils.generateQI([Ci.nsIObserver]),

    observe: function observe(subject, topic, data) {
        if (prefs.saved.get(this.version) == null)
            prefs.saved.set(this.version, prefs.check.get(this.version, true));

        if (prefs.saved.get(PREF_NIGHTLY) == null)
            prefs.saved.set(PREF_NIGHTLY, prefs.check.get(PREF_NIGHTLY, true));

        if (data === PREF) {
            prefs.check.set(this.version, prefs.get(PREF));
            prefs.check.set(PREF_NIGHTLY, prefs.get(PREF));
        }
    }
};

const SupportsString = Components.Constructor("@mozilla.org/supports-string;1", "nsISupportsString");

function Prefs(branch, defaults) {
    this.constructor = Prefs; // Ends up Object otherwise... Why?

    this.branch = Services.prefs[defaults ? "getDefaultBranch" : "getBranch"](branch || "");
    if (this.branch instanceof Ci.nsIPrefBranch2)
        this.branch.QueryInterface(Ci.nsIPrefBranch2);

    this.defaults = defaults ? this : new this.constructor(branch, true);
}
Prefs.prototype = {
    /**
     * Returns a new Prefs object for the sub-branch *branch* of this
     * object.
     *
     * @param {string} branch The sub-branch to return.
     */
    Branch: function Branch(branch) new this.constructor(this.root + branch),

    /**
     * Returns the full name of this object's preference branch.
     */
    get root() this.branch.root,

    /**
     * Returns the value of the preference *name*, or *defaultValue* if
     * the preference does not exist.
     *
     * @param {string} name The name of the preference to return.
     * @param {*} defaultValue The value to return if the preference has no value.
     * @optional
     */
    get: function get(name, defaultValue) {
        let type = this.branch.getPrefType(name);

        if (type === Ci.nsIPrefBranch.PREF_STRING)
            return this.branch.getComplexValue(name, Ci.nsISupportsString).data;

        if (type === Ci.nsIPrefBranch.PREF_INT)
            return this.branch.getIntPref(name);

        if (type === Ci.nsIPrefBranch.PREF_BOOL)
            return this.branch.getBoolPref(name);

        return defaultValue;
    },

    /**
     * Returns true if the given preference exists in this branch.
     *
     * @param {string} name The name of the preference to check.
     */
    has: function has(name) this.branch.getPrefType(name) !== 0,

    /**
     * Returns an array of all preference names in this branch or the
     * given sub-branch.
     *
     * @param {string} branch The sub-branch for which to return preferences.
     * @optional
     */
    getNames: function getNames(branch) this.branch.getChildList(branch || "", { value: 0 }),

    /**
     * Returns true if the given preference is set to its default value.
     *
     * @param {string} name The name of the preference to check.
     */
    isDefault: function isDefault(name) !this.branch.prefHasUserValue(name),

    /**
     * Sets the preference *name* to *value*. If the preference already
     * exists, it must have the same type as the given value.
     *
     * @param {name} name The name of the preference to change.
     * @param {string|number|boolean} value The value to set.
     */
    set: function set(name, value) {
        let type = typeof value;
        if (type === "string") {
            let string = SupportsString();
            string.data = value;
            this.branch.setComplexValue(name, Ci.nsISupportsString, string);
        }
        else if (type === "number")
            this.branch.setIntPref(name, value);
        else if (type === "boolean")
            this.branch.setBoolPref(name, value);
        else
            throw TypeError("Unknown preference type: " + type);
    },

    /**
     * Sets the preference *name* to *value* only if it doesn't
     * already have that value.
     */
    maybeSet: function maybeSet(name, value) {
        if (this.get(name) != value)
            this.set(name, value);
    },

    /**
     * Resets the preference *name* to its default value.
     *
     * @param {string} name The name of the preference to reset.
     */
    reset: function reset(name) {
        if (this.branch.prefHasUserValue(name))
            this.branch.clearUserPref(name);
    }
};

let prefs = new Prefs("");
prefs.check = prefs.Branch(PREF + ".");
prefs.saved = prefs.Branch("extensions.check-compatibility.saved.");
prefs.private = prefs.Branch("extensions.check-compatibility.");

let initialized = false;
function startup(data, reason) {
    if (!initialized) {
        initialized = true;
        listener.init(reason);
    }
}

function shutdown(data, reason) {
    if (reason != APP_SHUTDOWN)
        listener.cleanup();
}

function install(data, reason) {
    if (reason === ADDON_INSTALL)
        listener.install();
}

function uninstall(data, reason) {
    if (reason === ADDON_UNINSTALL)
        listener.uninstall();
}
