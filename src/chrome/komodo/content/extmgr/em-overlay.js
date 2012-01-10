/* Copyright (c) 2000-2011 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

if (!window.Cc) window.Cc = Components.classes;
if (!window.Ci) window.Ci = Components.interfaces;

Components.utils.import("resource://gre/modules/XPCOMUtils.jsm");
Components.utils.import("resource://gre/modules/Services.jsm");

// Main observer object - all the interesting logic is here
var gkoAMActionObserver = {
  // observer callback; dispatches to topic-specific methods
  observe: function gkoAMActionObserver_observe(subject, topic, data) {

    if (topic == "http-on-modify-request") {
      // Find the notificationCallbacks related to the request
      var httpChannel = subject.QueryInterface(Ci.nsIHttpChannel);
      try {
        var notificationCallbacks = httpChannel.notificationCallbacks ||
                                    httpChannel.loadGroup.notificationCallbacks;
      }
      catch (e) {
        return;
      }
      if (!notificationCallbacks) {
        return;
      }

      // Figure out what window we tried to load in; if it wasn't the addon
      // manager discover view, don't touch the request.
      try {
        var domWin = notificationCallbacks.getInterface(Ci.nsIDOMWindow);
        if (domWin.top !== document.getElementById("discover-browser").contentWindow) {
          return;
        }
      } catch (ex) {
        // Not a valid DOM Window - we don't care about it then.
        return;
      }

      // Figure out the root document we tried to load
      var documentChannel = notificationCallbacks.getInterface(Ci.nsIDocumentLoader).documentChannel || httpChannel;
      let uri = documentChannel.URI.spec;

      // this is a request from the discover pane; check for loads
      if (/\.xpi$/i.test(uri)) {
        // This is an extension installation; intercept the load, and force it
        // into the addon manager instead.  Otherwise the user will be
        // prompted to download the extension, which makes no sense.
        httpChannel.cancel(Components.results.NS_BINDING_ABORTED);
        gViewController.loadView("addons://list/extension");
        AddonManager.getInstallForURL(uri, function(aInstall) {
          AddonManager.installAddonsFromWebpage("application/x-xpinstall", this,
                                                null, [aInstall]);
        }, "application/x-xpinstall");
        return;
      }

      var goodPrefixes = [
        "http://community.activestate.com/addons/recommended",
        "http://community.activestate.com/xpi/",
        "http://community.activestate.com/files/",
        // Repeat for the support site (same server - different alias).
        "http://support.activestate.com/addons/recommended",
        "http://support.activestate.com/xpi/",
        "http://support.activestate.com/files/",
      ];
      for each (var prefix in goodPrefixes) {
        if (uri.substring(0, prefix.length) == prefix) {
          // prefix match, this is a whitelisted URL; load in the app.
          return;
        }
      }

      // Not one of the whitelisted prefixes; load this externally
      Cc["@mozilla.org/uriloader/external-protocol-service;1"]
        .getService(Ci.nsIExternalProtocolService)
        .loadURI(httpChannel.URI);
      httpChannel.cancel(Components.results.NS_BINDING_ABORTED);

      return;
    }

    var method = topic.replace(/^addon-install-/, "");
    subject instanceof Ci.amIWebInstallInfo; // silent QI
    if (method in this) {
      this.doCommand(method, subject);
    }
  },

  // wrapper for the various commands, to do the selection of the item, and
  // busy-wait for things to get ready
  doCommand: function(command, subject) {
    if (!subject.installs) {
      // don't know how to deal with this
      return;
    }
    if (!gViewController.viewObjects.list) {
      // not ready yet, ugh. Try again in a bit?
      setTimeout(gkoAMActionObserver.doCommand.bind(gkoAMActionObserver,
                                                    command,
                                                    subject),
                 10);
      return;
    }
    loadView("addons://list/extension");
    var installs = Array.slice(subject.installs);
    var callback = (function() {
      if (!this.box) {
        // not ready yet; try again later?
        setTimeout(callback, 10);
        return;
      }
      this[command](installs);

      // Try to select the item if we can.  This may fail if we're opening the
      // window right now, but that can't really be helped...
      setTimeout(function(id){
        var item = gListView.getListItemForID(id);
        if (item) {
          gListView._listBox.selectedItem = item;
          gListView._listBox.ensureElementIsVisible(item);
        }
      }, 10, installs[0].addon.id);
    }).bind(this);
    setTimeout(callback, 0);
  },

  // installation failure handler
  failed: function(installs) {
    for each (var install in installs) {
      var errorDetail = this.bundle.formatStringFromName("notification.failed",
                                                         [install.name],
                                                         1);
      if (!install.isCompatible) {
        var extBundle = Cc["@mozilla.org/intl/stringbundle;1"]
                        .getService(Ci.nsIStringBundleService)
                        .createBundle("chrome://mozapps/locale/extensions/extensions.properties");
        errorDetail = extBundle.formatStringFromName("details.notification.incompatible",
                                                     [install.name, this.brandShortName, this.appVersion],
                                                     3);
      }

      this.box.appendNotification(errorDetail,
                                  install.addon ? install.addon.id : install.sourceURI.spec,
                                  null,
                                  this.box.PRIORITY_WARNING_MEDIUM);
    }
  },

  complete: function(installs) {
    for each (var install in installs) {
      var opMask = AddonManager.PENDING_INSTALL | AddonManager.PENDING_UPGRADE;
      var addonOps = (install.addon.operationsRequiringRestart || 0);
      var buttons = [];
      if (opMask & addonOps) {
        buttons.push({
          label: this.bundle.GetStringFromName("notification.restart"),
          accessKey: "",
          callback: function() {
            Cc["@mozilla.org/toolkit/app-startup;1"]
              .getService(Ci.nsIAppStartup)
              .quit(Ci.nsIAppStartup.eAttemptQuit |
                    Ci.nsIAppStartup.eRestart);
          }
        });
      }
      this.box.appendNotification(this.bundle.formatStringFromName("notification.success",
                                                                   [install.name],
                                                                   1),
                                  install.addon ? install.addon.id : install.sourceURI.spec,
                                  null,
                                  this.box.PRIORITY_INFO_LOW,
                                  buttons);
    }
    // try to select the install. (no-op, doCommand handles it)
  },

  // complete, started doesn't need notification, the default behaviour is fine

  // XPCOM goop
  QueryInterface: XPCOMUtils.generateQI([Ci.nsIObserver]),

  // list of addon-install topics
  get topics() [
    "addon-install-started",
    "addon-install-disabled",
    "addon-install-blocked",
    "addon-install-failed",
    "addon-install-complete",
    "http-on-modify-request",
  ],

  // The notification box in which to display the errors
  get box() document.getElementById("ko-notificationbox"),

  // The string bundle
  get bundle() Cc["@mozilla.org/intl/stringbundle;1"]
                 .getService(Ci.nsIStringBundleService)
                 .createBundle("chrome://komodo/locale/extmgr.properties"),
  get brandShortName() Cc["@mozilla.org/intl/stringbundle;1"]
                 .getService(Ci.nsIStringBundleService)
                 .createBundle("chrome://branding/locale/brand.properties")
                 .GetStringFromName("brandShortName"),
  get appVersion() Services.appinfo.version

};

// Hook up and teardown for observers
addEventListener("load", function() {

  // Hide the themes category - as Komodo doesn't support themes.
  document.getElementById('category-theme').setAttribute('collapsed', 'true');

  // Hide the plugin check button in the Plugins category.
  Array.forEach(document.getElementsByClassName('global-info-plugincheck'),
                function(elem) { elem.setAttribute('collapsed', 'true')});

  for each (var topic in gkoAMActionObserver.topics) {
    Services.obs.addObserver(gkoAMActionObserver, topic, false);
  }
  var box = document.createElement("notificationbox");
  box.setAttribute("flex", 1);
  box.setAttribute("id", "ko-notificationbox");
  var spacer = document.querySelector("#header > spacer");
  spacer.parentNode.replaceChild(box, spacer);

  // Hide the community site navigation features.
  gDiscoverView.hideCommunitySiteNavigation = function(browser) {
    if (!browser)
      return;
    let browserSpec = browser.currentURI.spec.toLowerCase();
    if ((browserSpec.indexOf('://support.activestate.com/') >= 0) ||
        (browserSpec.indexOf('://community.activestate.com/') >= 0)) {
      for each (var id in ["as_header_wrapper", "as_footer_wrapper", "breadcrumb"]) {
        let elem = browser.contentDocument.getElementById(id);
        if (elem) {
          elem.hidden = true;
        }
      }
    }
  };
  gDiscoverView.hideCommunitySiteNavigation(document.getElementById("discover-browser"));

  // Replace the onStateChange handler to not show an error when the request was
  // deliberately cancelled by the "http-on-modify-request" observer (see above).
  gDiscoverView.__orig_onStateChange__ = gDiscoverView.onStateChange;
  gDiscoverView.onStateChange = function(aWebProgress, aRequest, aStateFlags, aStatus) {
    if (aStatus == Components.results.NS_BINDING_ABORTED) {
      // Aborted because it's an XPI file, but we want to treat it as a success.
      aStatus = Components.results.NS_OK;
      aRequest = null;
    }
    var result = gDiscoverView.__orig_onStateChange__(aWebProgress, aRequest, aStateFlags, aStatus);
    // Hide the community site nav elements when loaded:
    // Only care about the network events
    if (!(aStateFlags & (Ci.nsIWebProgressListener.STATE_IS_NETWORK)))
      return result;
    // Ignore anything except stop events
    if (!(aStateFlags & (Ci.nsIWebProgressListener.STATE_STOP)))
      return result;
    // Consider the successful load of about:blank as still loading
    if (aRequest instanceof Ci.nsIChannel && aRequest.URI.spec == "about:blank") {
      return result;
    }
    gDiscoverView.hideCommunitySiteNavigation(this._browser);
    return result;
  };

  // Force load everything in the same window, disable _blank
  var xulWindow = window.QueryInterface(Ci.nsIInterfaceRequestor)
                        .getInterface(Ci.nsIWebNavigation)
                        .QueryInterface(Ci.nsIDocShellTreeItem).treeOwner
                        .QueryInterface(Ci.nsIInterfaceRequestor)
                        .getInterface(Ci.nsIXULWindow);
  if (!xulWindow.XULBrowserWindow) {
    xulWindow.XULBrowserWindow = {
      setJSStatus: function(status) {},
      setJSDefaultStatus: function(status) {},
      setOverLink: function(link, element) {},
      onBeforeLinkTraversal: function(target, linkURI, linkNode, isAppTab) {
        // For some odd reason |target| can be quoted...
        return (target.replace(/["']/g, '') == "_blank") ? "_top" : target;
      },
      QueryInterface: XPCOMUtils.generateQI([Ci.nsIXULBrowserWindow])
    };
  }
}, false);

addEventListener("unload", function() {
  for each (var topic in gkoAMActionObserver.topics) {
    try {
      Services.obs.removeObserver(gkoAMActionObserver, topic);
    } catch (ex) { /* silent failure */ }
  }
}, false);
