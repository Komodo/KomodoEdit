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
 * The Original Code is Bookmarks Sync.
 *
 * The Initial Developer of the Original Code is Mozilla.
 * Portions created by the Initial Developer are Copyright (C) 2007
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 *  Myk Melez <myk@mozilla.org>
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

// This code was extracted from Komodo Sync to make it a part of the core that
// other functions of Komodo can access.

const EXPORTED_SYMBOLS = [];

const Cc = Components.classes;
const Ci = Components.interfaces;
const Cr = Components.results;
const Cu = Components.utils;
const CE = Components.Exception;

Cu.import("resource://gre/modules/XPCOMUtils.jsm");
Cu.import("resource://gre/modules/Services.jsm");

/**
 * Notification Manager Wrapper
 * This implements the JavaScript API on top of koINotificationManager
 * Note that there is one instance of the wrapper in the JSM, plus one for each
 * window. This is so that notifications originating from windows will
 * automatically have their window as the context.
 *
 * @note This is used in load-service.js (via the global) to create window-
 * specific wrappers.
 */
function KoNotificationManagerWrapper(aContext) {
  // we define .context oddly like this so that it doesn't get enumerated;
  // this makes for each (i in this) properly give just the notifications
  Object.defineProperty(this, "context", {
    value: (function() {
      if (!aContext) return null;
      if (aContext instanceof Ci.nsIInterfaceRequestor) {
        var winUtils = aContext.getInterface(Ci.nsIDOMWindowUtils);
        if (winUtils) {
          return "window-" + winUtils.outerWindowID;
        }
      }
      return String(aContext);
    })(),
    enumerable: false,
  });
}

XPCOMUtils.defineLazyServiceGetter(KoNotificationManagerWrapper.prototype, "_nm",
                                   "@activestate.com/koNotification/manager;1",
                                   "koINotificationManager");

KoNotificationManagerWrapper.prototype.add =
function KoNotificationManagerWrapper_add(aSummary, aTags, aIdentifier, aArgs) {
  var args = aArgs || {}; /* args are optional */
  var types = 0;
  if ("actions" in args) types |= Ci.koINotificationManager.TYPE_ACTIONABLE;
  if ("maxProgress" in args) {
    if (!(args.maxProgress > 0)) {
      throw CE("adding notification with maxProgress " + args.maxProgress + " not >0",
               Cr.NS_ERROR_INVALID_ARG);
    }
    types |= Ci.koINotificationManager.TYPE_PROGRESS;
  }
  if ("details" in args) types |= Ci.koINotificationManager.TYPE_TEXT;
  var notification = this._nm.createNotification(aIdentifier,
                                                 aTags,
                                                 aTags.length,
                                                 this.context,
                                                 types);
  // QI without throwing.  XPConnect flattens the QI results.
  notification instanceof Ci.koINotificationActionable;
  notification instanceof Ci.koINotificationProgress;
  notification instanceof Ci.koINotificationText;
  notification.summary = aSummary;
  var unknown_props = [];
  for (let [key, value] in Iterator(args)) {
    switch (key) {
      case "iconURL": case "severity": case "description": case "details":
      case "maxProgress": case "progress": case "sticky":
        notification[key] = value;
        break;
      case "actions":
        for (let action_data of value) {
          let action;
          if (action_data instanceof Ci.koINotificationAction) {
            action = action_data;
          } else {
            action = Cc["@activestate.com/koNotification/action;1"]
                       .createInstance(Ci.koINotificationAction);
            for (let [key, value] in Iterator(action_data)) {
              if (!(key in action)) {
                throw CE("invalid action argument " + key,
                         Cr.NS_ERROR_INVALID_ARG);
              }
              action[key] = value;
            }
          }
          notification.updateAction(action);
        }
        break;
      default:
        Services.console.logStringMessage("ko.notifications.add: unknown argument " + key);
    }
  }
  this._nm.addNotification(notification);
  return notification;
};

KoNotificationManagerWrapper.prototype.update =
function KoNotificationManagerWrapper_update(aNotification, aArgs) {
  var changed = false;
  if (!aNotification || !(aNotification instanceof Ci.koINotification)) {
    throw CE("invalid notification " + aNotification,
             Cr.NS_ERROR_INVALID_ARG);
  }
  for (let [key, value] in Iterator(aArgs || {})) {
    var valid_key = true;
    if (["summary", "details", "description", "severity"].indexOf(key) != -1) {
      if (key in aNotification) {
        aNotification[key] = value;
      } else {
        Services.console.logStringMessage("Notification does not have property " + key);
      }
    } else if (key == "progress") {
      if (value > (aNotification.maxProgress || Number.NEGATIVE_INFINITY)) {
        throw CE("Progress " + value + " is larger than maximum " + aNotification.maxProgress,
                 Cr.NS_ERROR_INVALID_ARG);
      }
      aNotification.progress = value;
    } else if (key == "maxProgress") {
      if (value !== Ci.koINotification.PROGRESS_INDETERMINATE &&
          value !== Ci.koINotification.PROGRESS_NOT_APPLICABLE)
      {
        if (aNotification.progress > value) {
          aNotification.progress = value;
        }
      }
      aNotification.maxProgress = value;
    } else if (key == "actions") {
      for each (let action_data in (value || [])) {
        if (!("identifier" in action_data)) {
          throw CE("Tried to update action without identifier",
                   Cr.NS_ERROR_INVALID_ARG);
        }
        if ("remove" in action_data) {
          aNotification.removeAction(action_data.identifier);
          continue;
        }
        var action = aNotification.getActions(action_data.identifier).shift();
        if (!action) {
          action = Cc["@activestate.com/koNotification/action;1"]
                     .createInstance(Ci.koINotificationAction);
          action.identifier = action_data.identifier;
        }
        for (let [key, value] in Iterator(action_data)) {
          if (key == "identifier") continue;
          if (!(key in action)) {
            throw CE("Unexpected property " + key + " on action " + action.identifier,
                     Cr.NS_ERROR_INVALID_ARG);
          }
          action[key] = value;
        }
        aNotification.updateAction(action);
      }
    } else {
      valid_key = false;
      var frame = Components.stack.caller;
      var message = Cc["@mozilla.org/scripterror;1"]
                      .createInstance(Ci.nsIScriptError);
      message.init("ko.notification.update: got unknown argument " + key,
                   frame.filename,
                   frame.sourceLine,
                   frame.lineNumber,
                   0,
                   Ci.nsIScriptError.warningFlag,
                   "XUL javascript");
      Services.console.logMessage(message);
    }
    if (valid_key) {
      changed = true;
    }
  }
  if (changed) {
    this._nm.addNotification(aNotification);
  }
};

KoNotificationManagerWrapper.prototype.remove =
function KoNotificationManagerWrapper_remove(aNotification) {
  this._nm.removeNotification(aNotification);
};

KoNotificationManagerWrapper.prototype.addListener =
function KoNotificationManagerWrapper_addListener(aListener) {
  this._nm.addListener(aListener);
};

KoNotificationManagerWrapper.prototype.removeListener =
function KoNotificationManagerWrapper_removeListener(aListener) {
  this._nm.removeListener(aListener);
};

/**
 * Use a Proxy to hook up some array-like features - .length and [0], [1] etc.
 * properties for accessing notifications. See
 * https://developer.mozilla.org/en/JavaScript/Reference/Global_Objects/Proxy
 */
KoNotificationManagerWrapper.prototype = Proxy.create((function(NMW)({
  getOwnPropertyDescriptor: function(name) {
    if (/^\d+$/.test(name)) {
      var index = parseInt(name, 10);
      if (index > -1 && index < NMW._nm.notificationCount) {
        return {
          enumerable: true,
          get: function() NMW._nm.getAllNotifications(index, index + 1).shift()
        };
      }
    }
    if (name == "length") {
      return { enumerable: false, get: function() NMW._nm.notificationCount };
    }
    if (NMW.hasOwnProperty(name)) {
      // forward to base prototype
      return { enumerable: false, get: function() NMW[name] };
    }
    if (Object.getPrototypeOf(NMW._nm).hasOwnProperty(name)) {
      // forward to koINotificationManager
      var Function = Components.utils.getGlobalForObject(NMW._nm).Function;
      if (NMW._nm[name] instanceof Function) {
        return { enumerable: false,
                 get: function() NMW._nm[name].bind(NMW._nm) };
      }
      return { enumerable: false, get: function() NMW._nm[name] };
    }
    // TODO: maybe consider importing things from Array.prototype?
    return undefined;
  },
  getPropertyDescriptor: function(name) {
    var p = this.getOwnPropertyDescriptor(name);
    if (p) return p;
    var o = NMW;
    while (o !== null) {
      p = Object.getOwnPropertyDescriptor(o, name);
      // make nothing enumerable so for...in loops work right
      if (p) {
        return Object.create(p, { enumerable: { value: false }});
      }
      o = Object.getPrototypeOf(o);
    }
    return undefined;
  },
  getOwnPropertyNames: function() {
    // array: [0, 1, 2, ... notificationCount - 1]
    var names = Object.keys(Array(NMW._nm.notificationCount + 1).join(".").split(""));
    names.unshift("length");
    // things from koINotificationManager
    var nm = Object.getPrototypeOf(NMW._nm);
    for each (var name in Object.getOwnPropertyNames(nm)) {
      if (name == "QueryInterface") continue;
      names.push(name);
    }
    dump("getOwnPropertyNames: " + names + "\n");
    return names;
  },
  getPropertyNames: function() {
    var set = {}; // use a hash to prevent duplicate names from showing up
    this.getOwnPropertyNames().map(function(key) set[key] = true);
    var o = NMW;
    while (o !== null) {
      for each (var key in Object.getOwnPropertyNames(o)) {
        set[key] = true;
      }
      o = Object.getPrototypeOf(o);
    }
    return Object.keys(set);
  },
  defineProperty: function(name, descriptor) {
    return Object.defineProperty(NMW, name, descriptor);
  },
  delete: function(name) false,
  fix: function() undefined,

  /** derived traps that for some reason Gecko doesn't supply **/
  has: function(name) {
    var result = !!this.getPropertyDescriptor(name);
    return result;
  },
  hasOwn: function(name) {
    var result = !!this.getOwnPropertyDescriptor(name);
    return result;
  },
  enumerate: function()
    this.getPropertyNames().filter((function(name) {
      var desc = this.getPropertyDescriptor(name);
      return desc ? desc.enumerable : false;
    }).bind(this)),
}))(KoNotificationManagerWrapper.prototype),
KoNotificationManagerWrapper.prototype);
