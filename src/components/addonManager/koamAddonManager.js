/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 *
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Software distributed under the License is distributed on an "AS IS" basis,
 * WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
 * for the specific language governing rights and limitations under the
 * License.
 *
 * The Original Code is AddonManager XPCOM wrapper.
 *
 * The Initial Developer of the Original Code is
 * Mook <marky+mozhg@activestate.com>.
 * Portions created by the Initial Developer are Copyright (C) 2011
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 *
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 *
 * ***** END LICENSE BLOCK ***** */


const Ci = Components.interfaces;
const Cu = Components.utils;

Cu.import("resource://gre/modules/XPCOMUtils.jsm");
Cu.import("resource://gre/modules/AddonManager.jsm");

["LOG", "WARN", "ERROR"].forEach(function(aName) {
  this.__defineGetter__(aName, function() {
    Components.utils.import("resource://gre/modules/AddonLogging.jsm");

    LogManager.getLogger("addons.xpcom", this);
    return this[aName];
  });
}, this);

var gAddonCache = {};
var gAddonInstallCache = [];
var gAddonInstallListenerCache = [];
var gAddonListenerCache = [];
var gUpdateListenerCache = [];

function getCachedValue(cache, item, wrapped) {
    var weak = null;
    if (item instanceof Ci.nsISupports) {
        if (item.wrappedJSObject) {
            item = item.wrappedJSObject;
        } else {
            weak = Components.utils.getWeakReference(item);
        }
    }
    for each (let entry in cache) {
        var ref = (entry[0] instanceof Ci.xpcIJSWeakReference) ? entry[0].get()
                                                               : entry[0];
        if (ref === item) {
            return entry[1];
        }
    }
    cache.push([weak || item, wrapped]);
    return wrapped;
}

/**
 * Given a Addon, return a koamIAddon
 */
function xpcAddon(aAddon) {
    if (!aAddon) return aAddon;
    if (aAddon.id in gAddonCache) {
        for each (let [js, xpc] in gAddonCache[aAddon.id])
            if (js == aAddon)
                return xpc;
    } else {
        // cache miss
        gAddonCache[aAddon.id] = [];
    }
    var wrapped = {
        findUpdates: function(listener, reason, appVersion, platformVersion)
            aAddon.findUpdates(jsUpdateListener(listener), reason,
                               appVersion, platformVersion),
        get hasContributors() Array.isArray(aAddon.contributors),
        getContributors: function(count) {
            if (!aAddon.contributors) return null;
            if (count) count.value = aAddon.contributors.length;
            return aAddon.contributors;
        },
        get hasDevelopers() Array.isArray(aAddon.developers),
        getDevelopers: function(count) {
            if (!aAddon.developers) return null;
            if (count) count.value = aAddon.developers.length;
            return aAddon.developers;
        },
        get hasTranslators() Array.isArray(aAddon.translators),
        getTranslators: function(count) {
            if (!aAddon.translators) return null;
            if (count) count.value = aAddon.translators.length;
            return aAddon.translators;
        },
        getScreenshots: function(count) {
            if (!aAddon.screenshots) return null;
            if (count) count.value = aAddon.screenshots.length;
            return aAddon.screenshots;
        },
        get installDate() aAddon.installDate.getTime() * 1000,
        get updateDate() aAddon.updateDate.getTime() * 1000,
        get install() xpcAddonInstall(aAddon.install),
        get pendingUpgrade() xpcAddon(aAddon.pendingUpgrade),
        get averageRating()
            aAddon.averageRating === null ? NaN : aAddon.averageRating,
        get reviewCount()
            aAddon.reviewCount === null ? -1 : aAddon.reviewCount,
        get totalDownloads()
            aAddon.totalDownloads === null ? -1 : aAddon.totalDownloads,
        get weeklyDownloads()
            aAddon.reviewCount === null ? -1 : aAddon.weeklyDownloads,
        get dailyUsers()
            aAddon.reviewCount === null ? -1 : aAddon.dailyUsers,
        get repositoryStatus()
            aAddon.repositoryStatus === null ? -1 : aAddon.repositoryStatus,
        QueryInterface: XPCOMUtils.generateQI([Ci.koamIAddon,
                                               Ci.nsISupportsWeakReference])
    };
    wrapped.__proto__ = aAddon;
    gAddonCache[aAddon.id].push([aAddon, wrapped]);
    return wrapped;
}

/**
 * Given an AddonInstall, return a koamIAddonInstall
 */
function xpcAddonInstall(aInstall) {
    if (!aInstall) return aInstall;
    var wrapped = {
        __proto__: aInstall,
        addListener: function(listener)
            aInstall.addListener(jsInstallListener(listener)),
        removeListener: function(listener)
            aInstall.removeListener(jsInstallListener(listener)),
        get existingAddon()
            xpcAddon(aInstall.existingAddon),
        get addon()
            xpcAddon(aInstall.addon),
        getLinkedInstalls: function(count) {
            if (!wrapped.linkedInstalls)
                return [];
            if (count)
                count.value = wrapped.linkedInstalls.length;
            return [].concat(wrapped.linkedInstalls);
        },
        QueryInterface: XPCOMUtils.generateQI([Ci.koamIAddonInstall,
                                               Ci.nsISupportsWeakReference])
    };
    wrapped.wrappedJSObject = wrapped;
    return getCachedValue(gAddonInstallCache, aInstall, wrapped);
}

/**
 * Given a koamIInstallListener, return a InstallListener
 */
function jsInstallListener(aListener) {
    var wrapped = {
        onNewInstall: function(install)
            aListener.onNewInstall(xpcAddonInstall(install)),
        onDownloadStarted: function(install)
            aListener.onDownloadStarted(xpcAddonInstall(install)),
        onDownloadProgress: function(install)
            aListener.onDownloadProgress(xpcAddonInstall(install)),
        onDownloadEnded: function(install)
            aListener.onDownloadEnded(xpcAddonInstall(install)),
        onDownloadCancelled: function(install)
            aListener.onDownloadCancelled(xpcAddonInstall(install)),
        onDownloadFailed: function(install)
            aListener.onDownloadFailed(xpcAddonInstall(install)),
        onInstallStarted: function(install)
            aListener.onInstallStarted(xpcAddonInstall(install)),
        onInstallEnded: function(install, addon)
            aListener.onInstallEnded(xpcAddonInstall(install),
                                     xpcAddon(addon)),
        onInstallCancelled: function(install)
            aListener.onInstallCancelled(xpcAddonInstall(install)),
        onInstallFailed: function(install)
            aListener.onInstallFailed(xpcAddonInstall(install)),
        onExternalInstall: function(addon, existingAddon, restart)
            aListener.onExternalInstall(xpcAddon(addon),
                                        xpcAddon(existingAddon),
                                        restart)
    };
    wrapped.wrappedJSObject = wrapped;
    return getCachedValue(gAddonInstallListenerCache, aListener, wrapped);
}

/**
 * Given a koamIAddonListener, return a AddonListener
 */
function jsAddonListener(aListener) {
    var wrapped = {
        onEnabling: function(addon, restart)
            aListener.onEnabling(xpcAddon(addon), restart),
        onEnabled: function(addon)
            aListener.onEnabled(xpcAddon(addon)),
        onDisabling: function(addon, restart)
            aListener.onDisabling(xpcAddon(addon), restart),
        onDisabled: function(addon)
            aListener.onDisabled(xpcAddon(addon)),
        onInstalling: function(addon, restart)
            aListener.onInstalling(xpcAddon(addon), restart),
        onInstalled: function(addon)
            aListener.onInstalled(xpcAddon(addon)),
        onUninstalling: function(addon, restart)
            aListener.onUninstalling(xpcAddon(addon), restart),
        onUninstalled: function(addon)
            aListener.onUninstalled(xpcAddon(addon)),
        onOperationCancelled: function(addon)
            aListener.onOperationCancelled(xpcAddon(addon)),
        onPropertyChanged: function(addon, properties)
            aListener.onPropertyChanged(xpcAddon(addon),
                                        properties,
                                        properties.length)
    };
    wrapped.wrappedJSObject = wrapped;
    return getCachedValue(gAddonListenerCache, aListener, wrapped);
}

/**
 * Given a koamIUpdateListener, return a UpdateListener
 */
function jsUpdateListener(aListener) {
    if (!aListener)
        return aListener;
    // the _existence_ of the methods gets checked (and different urls are
    // being used for update checks), so we can't have no-op stubs
    var wrapped = {};
    if (aListener.hasMethod("onCompatibilityUpdateAvailable"))
        wrapped.onCompatibilityUpdateAvailable = function(addon)
            aListener.onCompatibilityUpdateAvailable(xpcAddon(addon));
    if (aListener.hasMethod("onNoCompatibilityUpdateAvailable"))
        wrapped.onNoCompatibilityUpdateAvailable = function(addon)
            aListener.onNoCompatibilityUpdateAvailable(xpcAddon(addon));
    if (aListener.hasMethod("onUpdateAvailable"))
        wrapped.onUpdateAvailable = function(addon, install)
            aListener.onUpdateAvailable(xpcAddon(addon), xpcAddonInstall(install));
    if (aListener.hasMethod("onNoUpdateAvailable"))
        wrapped.onNoUpdateAvailable = function(addon)
            aListener.onNoUpdateAvailable(xpcAddon(addon));
    if (aListener.hasMethod("onUpdateFinished"))
        wrapped.onUpdateFinished = function(addon, error)
            aListener.onUpdateFinished(xpcAddon(addon), error);
    wrapped.wrappedJSObject = wrapped;
    return getCachedValue(gUpdateListenerCache, aListener, wrapped);
}

/**
 * Given a koamIAddonCallback, return a AddonCallback
 */
function jsAddonCallback(callback)
    callback && function(addon)
        callback.AddonCallback(xpcAddon(addon))

/**
 * Given a koamIAddonListCallback, return a AddonListCallback
 */
function jsAddonListCallback(callback)
    callback && function(addons)
        callback.AddonListCallback(addons.map(xpcAddon), addons.length)

/**
 * Given a koamIInstallCallback, return a InstallCallback
 */
function jsInstallCallback(callback)
    callback && function(install)
        callback.InstallCallback(xpcAddonInstall(install))

/**
 * Given a koamIInstallListCallback, return a InstallListCallback
 */
function jsInstallListCallback(callback)
    callback && function(installs)
        callback.InstallListCallback(installs.map(xpcAddonInstall),
                                     installs.length)

function amAddonManager() {
    // there's no point exposing the wrapper to JS.
    // (there's also no point getting the AddonManager via this service rather
    // than the JS module, but whatever)
    this.wrappedJSObject = AddonManager;
}

amAddonManager.prototype = {
    getInstallForURL: function(url, callback, mimetype, hash, name, iconURL,
                               version, loadGroup)
        AddonManager.getInstallForURL(url, jsInstallCallback(callback),
                                      mimetype, hash, name, iconURL,
                                      version, loadGroup),
    getInstallForFile: function(file, callback, mimetype)
        AddonManager.getInstallForFile(file,
                                       jsInstallCallback(callback),
                                       mimetype),
    getAllInstalls: function(callback)
        AddonManager.getAllInstalls(jsInstallListCallback(callback)),
    getInstallsByTypes: function(types, callback, typeCount)
        AddonManager.getInstallsByTypes(types, jsInstallListCallback(callback)),
    installAddonsFromWebpage: function()
        AddonManager.installAddonsFromWebpage.apply(AddonManager, Array.slice(arguments)),
    addInstallListener: function(listener)
        AddonManager.addInstallListener(jsInstallListener(listener)),
    removeInstallListener: function(listener)
        AddonManager.removeInstallListener(jsInstallListener(listener)),
    getAllAddons: function(callback)
        AddonManager.getAllAddons(jsAddonListCallback(callback)),
    getAddonByID: function(id, callback)
        AddonManager.getAddonByID(id, jsAddonCallback(callback)),
    getAddonsByIDs: function(ids, callback, idCount)
        AddonManager.getAddonsByIDs(ids, jsAddonListCallback(callback)),
    getAddonsByTypes: function(types, callback, typeCount)
        AddonManager.getAddonsByTypes(types, jsAddonListCallback(callback)),
    getAddonsWithOperationsByTypes: function(types, callback, typeCount)
        AddonManager.getAddonsWithOperationsByTypes(types,
                                                    jsAddonListCallback(callback)),
    addAddonListener: function(listener)
        AddonManager.addAddonListener(jsAddonListener(listener)),
    removeAddonListener: function(listener)
        AddonManager.removeAddonListener(jsAddonListener(listener)),
    isInstallAllowed: function(mimetype, uri)
        AddonManager.isInstallAllowed(mimetype, uri),
    isInstallEnabled: function(mimetype)
        AddonManager.isInstallEnabled(mimetype),

    // properties required for XPCOM registration (unused, see manifest):
    classDescription: "AddonManager XPCOM Wrapper",
    classID:          Components.ID("{15f8ee3a-1b7f-43c8-bdd9-6add07b52e1d}"),
    contractID:       "@mozilla.org/addons/addon-manager;1",
    
    QueryInterface: XPCOMUtils.generateQI([Ci.koamIAddonManager])
};

const NSGetFactory = XPCOMUtils.generateNSGetFactory([amAddonManager]);
