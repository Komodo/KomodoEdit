/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 * 
 * The contents of this file are subject to the Mozilla Public License
 * Version 1.1 (the "License"); you may not use this file except in
 * compliance with the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 * 
 * Software distributed under the License is distributed on an "AS IS"
 * basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
 * License for the specific language governing rights and limitations
 * under the License.
 * 
 * The Original Code is Komodo code.
 * 
 * The Initial Developer of the Original Code is ActiveState Software Inc.
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
 * ActiveState Software Inc. All Rights Reserved.
 * 
 * Contributor(s):
 *   ActiveState Software Inc
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

/* Feature status panel dialog.
 *
 * Usage:
 *  All dialog interaction is done via an object passed in and out as the first
 *  window argument: window.arguments[0]. All these arguments are optional.
 *      none
 *  On return window.arguments[0] has:
 *      none
 */

var fcplog = null;
//log.setLevel(ko.logging.LOG_DEBUG);

var gWidgets = {};
var gObserverSvc = null;
var gFeatureStatusObserver = null;
var gFeatureStatusSvc = null;


//---- internal support stuff

// all prefs we want to observe
var gPrefsList = [
        "nodejsDefaultInterpreter",
        "perlDefaultInterpreter","phpDefaultInterpreter",
        "pythonDefaultInterpreter","rubyDefaultInterpreter",
        "python3DefaultInterpreter",
                 ];

function FeatureStatusObserver() {
    gObserverSvc = Components.classes["@mozilla.org/observer-service;1"].
                       getService(Components.interfaces.nsIObserverService);
    gObserverSvc.addObserver(this, "feature_status_ready", false);
    var prefs = Components.classes["@activestate.com/koPrefService;1"].
                    getService(Components.interfaces.koIPrefService).prefs;
    for (var p in gPrefsList) {
        prefs.prefObserverService.addObserver(this, gPrefsList[p], 1); 
    }
};
FeatureStatusObserver.prototype.QueryInterface = function(aIID)
{
  if (aIID.equals(Components.interfaces.nsIObserver) ||
      aIID.equals(Components.interfaces.nsISupportsWeakReference) ||
      aIID.equals(Components.interfaces.nsISupports))
    return this;
  throw Components.results.NS_NOINTERFACE;
}
FeatureStatusObserver.prototype.destroy = function() {
    var prefs = Components.classes["@activestate.com/koPrefService;1"].
                    getService(Components.interfaces.koIPrefService).prefs;
    for (var p in gPrefsList) {
        prefs.prefObserverService.removeObserver(this, gPrefsList[p]); 
    }
    gObserverSvc.removeObserver(this, "feature_status_ready");
}
FeatureStatusObserver.prototype.observe = function(subject, topic, data)
{
    try {
        fcplog.info("observe(subject="+subject+", topic="+topic+
                 ", data="+data+")");

        // Observing (1) pref and (2) plain nsIObserver notifications.
        // Below we key on the notification "name", whose def'n
        // depends on the type of notification.
        var name;
        if (topic == "") {
            name = data;  // presumably this is a pref notification
        } else {
            name = topic; // a normal notification
        }


        switch (name) {
        case "feature_status_ready":
            var featureName = data;
            var featureStatus = subject;
            _updateFeatureControlPanel(featureName,
                                       featureStatus.status,
                                       featureStatus.reason);
            break;
        case "nodejsDefaultInterpreter":
            _requestFeatureStatus('Node.js Syntax Checking');
            break;
        case "perlDefaultInterpreter":
            _requestFeatureStatus('Perl Syntax Checking');
            break;
        case "phpDefaultInterpreter":
            _requestFeatureStatus('PHP Syntax Checking');
        case "pythonDefaultInterpreter":
            _requestFeatureStatus('Python Syntax Checking');
        case "python3DefaultInterpreter":
            _requestFeatureStatus('Python3 Syntax Checking');
        case "rubyDefaultInterpreter":
            _requestFeatureStatus('Ruby Syntax Checking');
        }
    } catch(ex) {
        fcplog.exception(ex);
    }
}


// Make a request to determine the status of the given feature.
//
//    "featureName" identifies the feature to get the status for. It
//        defaults to all features.
//
function _requestFeatureStatus(featureName)
{
    try {
        if (typeof(featureName) == "undefined" || !featureName) featureName = "*";
        fcplog.info("_requestFeatureStatus(featureName='"+featureName+"')");

        var dummy = new Object();
        if (featureName == "*") {
            var allFeatureNames = ["Node.js Syntax Checking",
                                   "Perl Syntax Checking",
                                   "PHP Syntax Checking",
                                   "Python Syntax Checking",
                                   "Python3 Syntax Checking",
                                   "Ruby Syntax Checking",
                                   ];
            for (var i = 0; i < allFeatureNames.length; i++) {
                try {
                    gObserverSvc.notifyObservers(dummy,
                        "feature_status_request", allFeatureNames[i]);
                } catch(ex) {
                    fcplog.exception(ex, "Error requesting status for '"+
                                      allFeatureNames[i]+"' feature");
                }
            }
        } else {
            try {
                gObserverSvc.notifyObservers(dummy, "feature_status_request",
                                             featureName);
            } catch(ex) {
                fcplog.exception(ex, "Error requesting status for '"+
                                  featureName+"' feature");
            }
        }
    } catch (ex) {
        fcplog.exception(ex, "_requestFeatureStatus error");
    }
}


// Update status in the feature control panel.
//
//    "featureName" names the feature.
//    "status" is a string describing the feature's status.
//    "reason" (optional) is a reason describing why the feature is not
//        functional.
//
function _updateFeatureControlPanel(featureName, status, reason)
{
    fcplog.info("_updateFeatureControlPanel");
    try {
        if (typeof(reason) == "undefined") {
            reason = null;
        }

        var widget = null;
        switch (featureName) {
        case "Node.js Syntax Checking":
            status = "Syntax Checking: " + status;
            widget = gWidgets.nodejsSyntaxCheckingStatus;
            break;
        case "Perl Syntax Checking":
            status = "Syntax Checking: " + status;
            widget = gWidgets.perlSyntaxCheckingStatus;
            break;
        case "PHP Syntax Checking":
            status = "Syntax Checking: " + status;
            widget = gWidgets.phpSyntaxCheckingStatus;
            break;
        case "Python Syntax Checking":
            status = "Syntax Checking: " + status;
            widget = gWidgets.pythonSyntaxCheckingStatus;
            break;
        case "Python3 Syntax Checking":
            status = "Syntax Checking: " + status;
            widget = gWidgets.python3SyntaxCheckingStatus;
            break;
        case "Ruby Syntax Checking":
            status = "Syntax Checking: " + status;
            widget = gWidgets.rubySyntaxCheckingStatus;
            break;
        }

        if (widget) {
            widget.setAttribute("value", status);
            if (reason) {
                widget.setAttribute("tooltip", "aTooltip");
                widget.setAttribute("tooltiptext", reason);
            } else {
                widget.removeAttribute("tooltip");
                widget.removeAttribute("tooltiptext");
            }
            var imageWidget = document.getElementById(widget.getAttribute('id') + '-image');
            if (imageWidget) {
                if (status.indexOf(': Ready') >= 0) {
                    imageWidget.setAttribute('class', 'status-ready');
                    imageWidget.removeAttribute("tooltiptext");
                } else {
                    imageWidget.setAttribute('class', 'status-error');
                    if (reason) {
                        imageWidget.setAttribute("tooltiptext", reason);
                    }
                }
            }
        }
    } catch (ex) {
        fcplog.exception(ex, "_updateFeatureControlPanel error");
    }
}


//---- interface routines for XUL

function OnLoad()
{
    fcplog = ko.logging.getLogger("dialogs.featureControlPanel");
    try {
        gWidgets.dialog = document.getElementById("dialog-featurecontrolpanel");
        gWidgets.cancelButton = gWidgets.dialog.getButton("cancel");
        gWidgets.nodejsSyntaxCheckingStatus = document.getElementById("nodejs-syntax-checking-status");
        gWidgets.perlSyntaxCheckingStatus = document.getElementById("perl-syntax-checking-status");
        gWidgets.phpSyntaxCheckingStatus = document.getElementById("php-syntax-checking-status");
        gWidgets.pythonSyntaxCheckingStatus = document.getElementById("python-syntax-checking-status");
        gWidgets.python3SyntaxCheckingStatus = document.getElementById("python3-syntax-checking-status");
        gWidgets.rubySyntaxCheckingStatus = document.getElementById("ruby-syntax-checking-status");

        gWidgets.cancelButton.setAttribute("label", "Close");
        gWidgets.cancelButton.setAttribute("accesskey", "C");

        gFeatureStatusObserver = new FeatureStatusObserver();

        // we merely get a handle on the service to make sure it's been started
        gFeatureStatusSvc = Components.classes["@activestate.com/koFeatureStatusService;1"].
            getService(Components.interfaces.koIFeatureStatusService);

        _requestFeatureStatus("*");

        window.sizeToContent();
    } catch(ex) {
        fcplog.exception(ex, "Error loading feature status panel dialog.");
    }
}


function OnUnload()
{
    try {
        gFeatureStatusObserver.destroy();
        gFeatureStatusObserver = null;
    } catch(ex) {
        fcplog.exception(ex);
    }
}


function LaunchHelp(page)
{
    try {
        opener.ko.help.open(page);
    } catch(ex) {
        fcplog.exception(ex);
    }
}


function LaunchPrefs(panel)
{
    try {
        opener.prefs_doGlobalPrefs(panel);
    } catch(ex) {
        fcplog.exception(ex);
    }
}


function Cancel()
{
    try {
        return true;
    } catch(ex) {
        fcplog.exception(ex);
    }
    return false;
}


