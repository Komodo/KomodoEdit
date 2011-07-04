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
  for each (var topic in gkoAMActionObserver.topics) {
    Services.obs.addObserver(gkoAMActionObserver, topic, false);
  }
  var box = document.createElement("notificationbox");
  box.setAttribute("flex", 1);
  box.setAttribute("id", "ko-notificationbox");
  var spacer = document.querySelector("#header > spacer");
  spacer.parentNode.replaceChild(box, spacer);
}, false);

addEventListener("unload", function() {
  for each (var topic in gkoAMActionObserver.topics) {
    try {
      Services.obs.removeObserver(gkoAMActionObserver, topic);
    } catch (ex) { /* silent failure */ }
  }
}, false);
