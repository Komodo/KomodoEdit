/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Global defines to be used throughout Komodo code base.
 */

const Cc = Components.classes;
const Ci = Components.interfaces;
const Cu = Components.utils;

/**
 * Global utility modules.
 */
const {Services} = Cu.import("resource://gre/modules/Services.jsm");
const {XPCOMUtils} = Cu.import("resource://gre/modules/XPCOMUtils.jsm");

/**
 * Define the main Komodo namespace.
 */
if (typeof(ko) == 'undefined') {
    var ko = {};
}

/* Komodo version */
ko.version = "PP_KOMODO_VERSION";

// Prepare window.console so jetpack doesnt instantiate its own
Services.scriptloader.loadSubScript("chrome://komodo/content/sdk/console.js");

// Jetpack must be loaded after window.ko has been created (so that it
// knows how to get things into the right scope, for backwards compat)
Services.scriptloader.loadSubScript("chrome://komodo/content/jetpack.js");
JetPack.defineDeprecatedProperty(ko, "logging", "ko/logging", {since: "9.0.0a1"});
JetPack.defineDeprecatedProperty(ko, "printing", "ko/printing", {since: "9.0.0a1"});

/**
 * Global Komodo services, defined on the Services object (once per app).
 */
if (!Services.koInfo) {
    XPCOMUtils.defineLazyGetter(Services, "koInfo", () =>
        Cc["@activestate.com/koInfoService;1"].getService(Ci.koIInfoService));

    XPCOMUtils.defineLazyGetter(Services, "koDirs", () =>
        Cc["@activestate.com/koDirs;1"].getService(Ci.koIDirs));

    XPCOMUtils.defineLazyGetter(Services, "koFileSvc", () =>
        Cc["@activestate.com/koFileService;1"].getService(Ci.koIFileService));

    XPCOMUtils.defineLazyGetter(Services, "koFileStatus", () =>
        Cc["@activestate.com/koFileStatusService;1"].getService(Ci.koIFileStatusService));

    XPCOMUtils.defineLazyGetter(Services, "koDocSvc", () =>
        Cc["@activestate.com/koDocumentService;1"].getService(Ci.koIDocumentService));

    XPCOMUtils.defineLazyGetter(Services, "koViewSvc", () =>
        Cc["@activestate.com/koViewService;1"].getService(Ci.koIViewService));

    XPCOMUtils.defineLazyGetter(Services, "koTextUtils", () =>
        Cc["@activestate.com/koTextUtils;1"].getService(Ci.koITextUtils));

    XPCOMUtils.defineLazyGetter(Services, "koEncodingSvc", () =>
        Cc["@activestate.com/koEncodingServices;1"].getService(Ci.koIEncodingServices));

    XPCOMUtils.defineLazyGetter(Services, "koSysUtils", () =>
        Cc["@activestate.com/koSysUtils;1"].getService(Ci.koISysUtils));

    XPCOMUtils.defineLazyGetter(Services, "koLangRegistry", () =>
        Cc["@activestate.com/koLanguageRegistryService;1"].getService(Ci.koILanguageRegistryService));

    XPCOMUtils.defineLazyGetter(Services, "koAsync", () =>
        Cc["@activestate.com/koAsyncService;1"].getService(Ci.koIAsyncService));

    XPCOMUtils.defineLazyGetter(Services, "koRun", () =>
        Cc["@activestate.com/koRunService;1"].getService(Ci.koIRunService));

    XPCOMUtils.defineLazyGetter(Services, "koFind", () =>
        Cc["@activestate.com/koFindService;1"].getService(Ci.koIFindService));

    XPCOMUtils.defineLazyGetter(Services, "koOs", () =>
        Cc["@activestate.com/koOs;1"].getService(Ci.koIOs));

    XPCOMUtils.defineLazyGetter(Services, "koOsPath", () =>
        Cc["@activestate.com/koOsPath;1"].getService(Ci.koIOsPath));

    XPCOMUtils.defineLazyGetter(Services, "koLastError", () =>
        Cc["@activestate.com/koLastErrorService;1"].getService(Ci.koILastErrorService));

    XPCOMUtils.defineLazyGetter(Services, "koUserEnv", () =>
        Cc["@activestate.com/koUserEnviron;1"].getService(Ci.koIUserEnviron));

    XPCOMUtils.defineLazyGetter(Services, "koRemoteConnection", () =>
        Cc["@activestate.com/koRemoteConnectionService;1"].getService(Ci.koIRemoteConnectionService));

    XPCOMUtils.defineLazyGetter(Services, "koWebbrowser", () =>
        Cc["@activestate.com/koWebbrowser;1"].getService(Ci.koIWebbrowser));
}
