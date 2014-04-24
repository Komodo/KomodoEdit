// Copyright (c) 2000-2011 ActiveState Software Inc.
// See the file LICENSE.txt for licensing information.

/**
 *
 * stackato.js -- JS code for the Stackato interface
 *
 */

if (typeof(ko)==='undefined') {
    var ko = {};
}
if (typeof(ko.stackato)==='undefined') {
    ko.stackato = {};
}
xtk.include("domutils");
var widgets = {};
var _stackatoWindow = window;
(function() {

var bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://stackatotools/locale/stackato.properties");
var log;

var gko = null;
var gWindow = null;
var gStackatoPrefs;
var terminalView = null;
var g_terminalHandler = null;
var g_shuttingDown = false;
var g_finishedInit = false;

var firstTimeRun = false;
const CurrentStackatoVersion = 2;
/**
 * Lastest stackato version known for prefs file
 * 2: Komodo 7.1.0: s/stackato.mru/mruStackatoTargetList/
 * 1: Komodo 7.0 : first version
 */


this.focus = function() {
    setTimeout(function() {
        _stackatoWindow.focus();
    }, 100);
};

this.onLoad = function() {
    gWindow = window.arguments[0].window;
    gko = window.arguments[0].ko;
    log = gko.logging.getLogger("stackato");
    
    scintillaOverlayOnLoad();
    terminalView = document.getElementById("stackato_output_view");
    terminalView.init();

    g_terminalHandler = Components.classes['@activestate.com/koTerminalHandler;1']
                        .createInstance(Components.interfaces.koITerminalHandler);
    terminalView.initWithTerminal(g_terminalHandler);

    setTimeout(function(this_) {
        // show the window first, then set things up.
        try {
            this_.initialize();
            this_.sanityCheck_then_getCurrentTarget();
        } catch(ex) {
            log.exception(ex, "Error in onLoad: ");
        }
    }, 1000, this);
};

this.initialize = function() {
    this.treeNames = ["mainTree", "servicesProvisionedTree",
                      "servicesSystemTree", "frameworksTree", "runtimesTree", "targetsTree"];
    this.treeChildrenNames = ["mainTree_treechildren",
                           "servicesProvisionedTree_treechildren",
                           "servicesSystemTree_treechildren",
                           "frameworksTree_treechildren",
                           "runtimesTree_treechildren",
                           "targetsTree_treechildren"
                           ];
    this.stackatoService = Components.classes["@activestate.com/koStackatoServices;1"]
            .getService(Components.interfaces.koIStackatoServices);
    this.stackatoService.initialize();
    
    widgets.fields = {};
    
    for each (var name in [
        "target_textbox", "change_target_button",
        "user_logged_in", "user1_textbox", "change_user1_button",
        "user_logged_out", "user2_textbox", "user2_password", "change_user2_button"
    ]) {
        widgets.fields[name] = document.getElementById(name);
    }
    
    widgets.trees = {};
    widgets.views = {};
    for each (var name in this.treeNames) {
        widgets[name] = widgets.trees[name] = document.getElementById(name);
    }
    this.servicesTreeManager = new ko.stackato.trees.ServicesTreeManager();

    this.user = this.password = "";
    this._target = null;
    this._updateButtons();
    this.runtimeNames = [];
    this.frameworkNames = [];
    this.provisionedServiceNames = [];
    this.systemServiceNames = [];
    this.targetNames = [],
    this.hasLoggedOut = false;
    this.pendingRequests = {};

    this.finishBuildingToolbar("stackato_apps_toolbar");
    
    var nsIDOMKeyEvent = Components.interfaces.nsIDOMKeyEvent;
    this.arrowKeys = [nsIDOMKeyEvent.DOM_VK_UP,
                      nsIDOMKeyEvent.DOM_VK_DOWN,
                      nsIDOMKeyEvent.DOM_VK_LEFT,
                      nsIDOMKeyEvent.DOM_VK_RIGHT];

    if (!gko.prefs.hasPref("stackato")) {
        firstTimeRun = true;
        gStackatoPrefs = Components.classes["@activestate.com/koPreferenceSet;1"].createInstance();
        gko.prefs.setPref("stackato", gStackatoPrefs);
        gko.prefs.setLongPref("mruStackatoTargetSize", 10);
    } else {
        gStackatoPrefs = gko.prefs.getPref("stackato");
        if (!gStackatoPrefs.hasPref("notFirstTime")
            || !gStackatoPrefs.getBooleanPref("notFirstTime")) {
            firstTimeRun = true;
        }
        this._upgradeByVersion(gStackatoPrefs);
    }
    gStackatoPrefs.setLongPref("version", CurrentStackatoVersion);
    if (!gStackatoPrefs.hasPref("apps")) {
        gStackatoPrefs.setPref("apps", Components.classes["@activestate.com/koPreferenceSet;1"].createInstance());
    }
    if (!gStackatoPrefs.hasPref("boxIsClosed")) {
        // No longer needed: use mozilla persist to track state of collapsers
        gStackatoPrefs.deletePref("boxIsClosed");
    }
    if (gStackatoPrefs.hasPref("groupNamesByTarget")) {
        try {
            this.groupNamesByTarget = JSON.parse(gStackatoPrefs.getStringPref("groupNamesByTarget"));
        } catch(ex) {
            log.exception(ex, "Error json-parsing " + gStackatoPrefs.getStringPref("groupNamesByTarget"));
            this.groupNamesByTarget = {};
        }
    } else {
        this.groupNamesByTarget = {};
    }
    this.showEnvironmentVariables = false;
    
    // Init the panel splitters.
    ko.stackato.toggleProvisionedServices(
        document.getElementById("toggleProvisionedServicesButton"), false);
    ko.stackato.toggleOutputView(
        document.getElementById("toggleOutputWindowButton"), false);
    ko.stackato.toggleFrameworksAndRuntimes(
        document.getElementById("toggleFrameworksAndRuntimesButton"), false);
    ko.stackato.toggleTargets(
        document.getElementById("toggleTargetsButton"), false);
    

    terminalView.startSession(true);
    this._clearTerminal = true;
    this._getTargetsUpdateTargetMenu(this.targetNames, /*getGroups=*/false);

    //TODO: Prevent sorting in the main tree.  The problem is that the
    // tree.xml handler handles the eventPhase = atTarget value, which
    // addEventListener doesn't handle, and an attempt to set up a binding failed.
    
    //var mainTreecols = Array.slice(widgets.trees.mainTree.getElementsByTagName("treecol"))
    //// The clicks are handled at phase="target"; so set useCapture to false
    //for each (var treecol in mainTreecols) {
    //    treecol.addEventListener("click", this.handleMainTreecolClick, true);
    //    treecol.addEventListener("click", this.handleMainTreecolClick, false);
    //}

    
};

this._upgradeByVersion = function(gStackatoPrefs) {
    try {
        var version = (gStackatoPrefs.hasPref("version")
                       ? gStackatoPrefs.getLongPref("version")
                       : 1);
        if (version == 1) {
            // Rename pref stackato.mru to mruStackatoTargetList
            var oldestFirstList = gko.mru.getAll("stackato.mru");
            // This should be done by the mru module
            gko.prefs.setLongPref("mruStackatoTargetSize", 10);
            if (oldestFirstList.length > 10) {
                // Drop delta oldest stackato.mru items
                oldestFirstList.splice(0, oldestFirstList.length - 10);
            }
            oldestFirstList.forEach(function(target) {
                    gko.mru.add("mruStackatoTargetList", target, true);
                });
            // Again ko.mru should provide a way of doing this
            gko.prefs.deletePref("stackato.mru");
        }
    } catch(ex) {
        log.exception(ex, "stackato.js: _upgradeByVersion: failed");
    }
}

//this.handleMainTreecolClick = function(event) {
//    // squelch sort.
//    event.stopPropagation();
//    event.preventDefault();
//};

this._attributesToCopy = ['oncommand', 'disableUnless', 'disableIf'];

this.finishBuildingToolbar = function(toolbar_id) {
    var toolbar = document.getElementById(toolbar_id);
    var childNodes = toolbar.childNodes;
    var i, j, targetNode, srcNode, srcId, attributes, attrLen, attrNode;
    for (i = 0; i < childNodes.length; i++) {
        targetNode = childNodes[i];
        srcId = targetNode.getAttribute("inheritFrom");
        if (!srcId || !(srcNode = document.getElementById(srcId))) {
            continue;
        }
        attributes = srcNode.attributes;
        attrLen = attributes.length;
        for (j = 0; j < attrLen; ++j) {
            attrNode = attributes[j];
            if (this._attributesToCopy.indexOf(attrNode.name) >= 0) {
                targetNode.setAttribute(attrNode.name, attrNode.value);
            }
        }
    }
};    

this.updateTarget = function() {
    //TODO: Try to switch to the new target.  If it fails, revert to
    // this._target, and we'll stay logged in.
    var newTarget = widgets.fields.target_textbox.value;
    if (newTarget && newTarget != this._target) {
        var this_ = this;
        var badTargetFunc = function(data) {
            ko.dialogs.alert(bundle.formatStringFromName("Stackato X ERROR", ["change target failed", data], 2));
            // Don't do anything else.
        };
        var handler = {
          onError: function(data) {
                badTargetFunc(data);
            },
          setData: function(data) {
                //log.warn("target: setData: " + data + "\n");
                //dump("updateTarget: target: " + newTarget
                //     + ", result: "
                //     + data + "\n");
                if (data.indexOf("Host is not valid") == 0) {
                    badTargetFunc(data);
                } else {
                    this_.stackatoService.target = this_._target = newTarget;
                    this_._disableChangeTargetButton(true);
                    this_.addActiveTarget(newTarget);
                    this_.getUserWithCurrentTarget(newTarget);
                    gko.mru.add("mruStackatoTargetList", newTarget, true);
                }
            }
        };
        this.wrapCallbackFunction("runCommand",
                                  "target_label",
                                  handler, null, false,
                                  ["target", newTarget, "--no-prompt"]);
    }
};

this._showLoggedOutFields = function(user, password) {
    widgets.fields.user_logged_in.setAttribute("hidden", true);
    widgets.fields.user_logged_out.setAttribute("hidden", false);
    widgets.fields.user1_textbox.value = user;
    widgets.fields.user2_textbox.value = user;
    widgets.fields.user2_password.value = password;
};

this._showLoggedInFields = function(user, password) {
    widgets.fields.user_logged_in.setAttribute("hidden", false);
    widgets.fields.user_logged_out.setAttribute("hidden", true);
    widgets.fields.user1_textbox.value = user;
    widgets.fields.user2_textbox.value = user;
    widgets.fields.user2_password.value = password;
};

this._updateButtons = function() {
    var isLoggedIn = !!this.user;
    var buttonIds = [
        "showTargetInfo", "showRuntimes", "showFrameworks", "showServices", "maintree_refresh",
        "maintree_show_env",
        "stb_update", "stb_restart", "stb_restart", "stb_start", "stb_stop",
        "stb_rename", "stb_delete", "stb_add"];
    // Should be global only
    buttonIds = [
        "showTargetInfo", "showRuntimes", "showFrameworks", "showServices", "maintree_refresh",
        "maintree_show_env",
        "stb_add"];
    var func = ((isLoggedIn && g_finishedInit)
                ? function(id) { document.getElementById(id).removeAttribute("disabled"); }
                : function(id) { document.getElementById(id).setAttribute("disabled", true); })
    buttonIds.forEach(func);
};
this.login = function() {
    var user = widgets.fields["user2_textbox"].value;
    if (!user) {
        alert("no user supplied");
        return;
    }
    var password = widgets.fields["user2_password"].value;
    var this_ = this;
    this.hasLoggedOut = false;
    var handler = {
      setData: function(data) {
            // Hardwired string from Stackato client, do not i18nize
            if (data && data.indexOf("Successfully logged into") >= 0) {
                this_.user = user;
                gko.mru.add("stackato-usernameMru", user, true);
                this_.password = password;
                this_._showLoggedInFields(this_.user, this_.password);
                this_.Credentials.addEntry(this_._target, user, password)
                this_._updateButtons();
                this_.setupApplicationsTree(true);
            } else {
                // Hardwired string from Stackato client, do not i18nize
                if (data && data.indexOf("Problem with login, invalid account or password") >= 0) {
                    ko.dialogs.alert(data);
                }
                this_.user = '';
                this_.password = '';
                this_._updateButtons();
                this_._showLoggedOutFields(user, password);
            }
        }
    };
    this.wrapCallbackFunction("login", "user2_label",
                              handler,
                              null, false, [user, password]);
};

this.logout = function(callback) {
    if (typeof(callback) == "undefined") callback = null;
    var this_ = this;
    var handler = {
      setData: function(data) {
            // Hardwired string from Stackato client, do not i18nize
            if (data && data.indexOf("Successfully logged out of") != 0) {
                log.error("Expecting logged out msg, got " + data);
            }
            this_.hasLoggedOut = true;
            var passwordToCache;
            if (this_.password) {
                passwordToCache = this_.password;
            } else {
                var userName;
                [userName, passwordToCache] = this_.Credentials.credentialsForHostname(this_._target);
            }
            this_._showLoggedOutFields(this_.user, passwordToCache || "");
            this_.checkLogin();
            this_.clearTrees();
            this_.user = '';
            this_.password = '';
            this_._updateButtons();
        }
    };
    this.wrapCallbackFunction("logout", "user1_label",
                              handler,
                              callback,
                              /*useJSON=*/false);
};

this.checkLogin = function() {
    widgets.fields.change_user2_button.disabled = (
        !widgets.fields.user2_textbox.value
        || !widgets.fields.user2_password.value);
    
};

this.checkUpdateTarget = function(event, menulist) {
    var newTarget = widgets.fields.target_textbox.value;
    this._disableChangeTargetButton(!newTarget);
    if (event.charCode == 0
        && !event.shiftKey
        && !event.ctrlKey
        && !event.metaKey
        && (event.keyCode == event.DOM_VK_RETURN)) {
        this.updateTarget();
    }
};

this._disableChangeTargetButton = function(disabledStatus) {
    widgets.fields.change_target_button.disabled = disabledStatus;
};

this._addStyle = function _addStyle(node, value) {
    var style = node.getAttribute("style");
    if (style) {
        style += " " + value;
    } else {
        style = value;
    }
    node.setAttribute("style", value);
}

this.setSquirreledFlex = function(node) {
    if (node.hasAttribute("koSquirreledFlex")) {
        node.setAttribute("flex",
                          node.getAttribute("koSquirreledFlex"));
    }
};

this.zeroAndSquirrelFlex = function(node) {
    var flex = node.getAttribute("flex");
    if (flex) {
        node.setAttribute("koSquirreledFlex", flex);
        node.setAttribute("flex", "0");
    }
};

this.closeToggleBox = function(vboxNode, targetNodes, imageNode) {
    for each (var targetNode in targetNodes) {
        this._addStyle(targetNode, 'visibility: collapse;');
        this.zeroAndSquirrelFlex(targetNode);
    }
    this.zeroAndSquirrelFlex(vboxNode);
    this._addStyle(vboxNode, 'visibility: collapse;');
    imageNode.setAttribute("tooltiptext", "show pane");
};

this.openToggleBox = function(vboxNode, targetNodes, imageNode) {
    for each (var targetNode in targetNodes) {
        this._addStyle(targetNode, 'visibility: visible;');
        this.setSquirreledFlex(targetNode);
    }
    this.setSquirreledFlex(vboxNode);
    this._addStyle(vboxNode, 'visibility: visible;');
    imageNode.setAttribute("tooltiptext", "hide pane");
};

this.showTreeColumn = function(node) {
    node.removeAttribute('hidden');
}

this.hideTreeColumn = function(node) {
    node.setAttribute('hidden', 'true');
};

this.toggleByName = function(names, isChecked) {
    var func = isChecked ? this.showTreeColumn : this.hideTreeColumn;
    names.forEach(function(name) {
        func(document.getElementById(name));
    });
};

this.toggleShowEnvironment = function(checkbox) {
    var checked = checkbox.checked;
    this.showEnvironmentVariables = checked;
    gStackatoPrefs.setBooleanPref("showEnvironment", checked);
    this.doToggleShowEnvironment(checked);
}

this.toggleButtonAndFrame = function(toolbarbutton, mainNode, imageNode, doToggle) {
    if (doToggle) {
        var state = toolbarbutton.getAttribute("state");
        switch(state) {
        case "collapsed":
            toolbarbutton.setAttribute("state", "open");
            break;
        case "open":
        default:
            toolbarbutton.setAttribute("state", "collapsed");
            break;
        }
    }
    var treeNodes = Array.slice(mainNode.getElementsByTagName("tree"));
    this._updateSubpanelFromState(toolbarbutton, mainNode, treeNodes, imageNode);
};

this.toggleFrameworksAndRuntimes = function(toolbarbutton, doToggle) {
    var mainNode = document.getElementById("frameworks_runtimes_hbox");
    var imageNode = document.getElementById("frameworks_runtimes_button");
    this.toggleButtonAndFrame(toolbarbutton, mainNode, imageNode, doToggle);
};

this.toggleProvisionedServices = function(toolbarbutton, doToggle) {
    var mainNode = document.getElementById("vbox_provisioned_services");
    var imageNode = document.getElementById("provisioned_services_button");
    this.toggleButtonAndFrame(toolbarbutton, mainNode, imageNode, doToggle);
};

this.toggleOutputView = function(toolbarbutton, doToggle) {
    var mainNode = document.getElementById("stackato_output_view");
    var imageNode = document.getElementById("output_view_button");
    this.toggleButtonAndFrame(toolbarbutton, mainNode, imageNode, doToggle);
};

this.toggleTargets = function(toolbarbutton, doToggle) {
    var mainNode = document.getElementById("vbox_targets");
    var imageNode = document.getElementById("toggleTargetsButton");
    this.toggleButtonAndFrame(toolbarbutton, mainNode, imageNode, doToggle);
};

this._updateSubpanelFromState = function(toolbarbutton, vboxNode, treeNodes, imageNode) {
    var state = toolbarbutton.getAttribute("state");
    switch(state) {
        case "collapsed":
            this.closeToggleBox(vboxNode, treeNodes, imageNode);
            toolbarbutton.setAttribute("tooltiptext", "Show the Provisioned Services Subpanel");
            break;
        case "open":
        default:
            this.openToggleBox(vboxNode, treeNodes, imageNode);
            toolbarbutton.setAttribute("tooltiptext", "Hide the Provisioned Services Subpanel");
            break;
    }
}

this.getAndUpdateEnvironmentVarsForAppname = function(view, appName, callback) {
    var handler = {
      onError: function() { log.debug("env appName failed"); } ,
      onStopped: function(){ log.debug("env appName was stopped"); },
      setData: function(results) {
          view.addEnvironmentData(appName, results);
      }
    };
    this.wrapCallbackFunction("runCommand",
                              "applications_button",
                              handler,
                              callback,
                              true, /*useJSON */
                              ["env", appName, "--json"]);
};

this.doToggleShowEnvironment = function(checked, callback) {
    var names = ["post_url", "env_name", "post_env_name", "env_value"];
    if (typeof(callback) == "undefined") callback = null;
    var view = widgets.views.mainTree;
    view.setEnvironmentValueStatus(checked);
    if (!checked) {
        view.removeEnvValuesFromTree();
        this.toggleByName(names, false);
        if (callback) callback();
    } else {
        var appNames = view.getNames();
        var appName;
        var this_ = this;
        var updateFunc = function(i) {
            if (i >= appNames.length) {
                this_.toggleByName(names, true);
                if (callback) callback();
            } else {
                this_.getAndUpdateEnvironmentVarsForAppname(view, appNames[i],
                                                            function() {
                                                                updateFunc(i + 1)
                                                                    });
            }
        }
        updateFunc(0);
    }
    
};

this.toggleShowStatistics = function(checkbox) {
    var names = ["post_env_value", "stats_instance_num", "post_stats_instance_num",
                 "stats_cpu_cores", "post_stats_cpu_cores", "stats_memory_limit",
                 "post_stats_memory_limit", "stats_disk_limit", "post_stats_disk_limit",
                 "stats_uptime", "post_stats_uptime"
                 ];
    var checked = checkbox.checked;
    widgets.views.mainTree.showStatistics = checked;
    this.toggleByName(names, checked);
};

this.toggleShowPassword = function(checkbox, password_id) {
    var checked = checkbox.checked;
    var textbox = document.getElementById(password_id);
    if (checked) {
        textbox.removeAttribute('type');
    } else {
        textbox.setAttribute('type', 'password');
    }
};

this.showTargetInfo = function() {
    this._clearTerminal = true;
    this.doApplicationCommand(["info"], null);
};

this.showRuntimes = function() {
    this._clearTerminal = true;
    this.doApplicationCommand(["runtimes"], null);
};

this.showFrameworks = function() {
    this._clearTerminal = true;
    this.doApplicationCommand(["frameworks"], null);
};

this.showServices = function() {
    this._clearTerminal = true;
    this.doApplicationCommand(["services"], null);
};

this.visitStackatoHelpPage = function() {
    gko.browse.openUrlInDefaultBrowser("http://docs.stackato.com/");
};

this.visitStackatoHomePage = function() {
    gko.browse.openUrlInDefaultBrowser("http://www.activestate.com/cloud");
};

this.serverRefusedConnectionRE = /^\[?Server.*?refused connection/;
this.wrapCallbackFunction = function(methodName,
                                     toggleButtonID,
                                     dataHandler,
                                     nextFunc,
                                     useJSON,
                                     args,
                                     alwaysCallNextFunc) {
    if (g_shuttingDown) {
        return null;
    }
    var this_ = this;
    if (typeof(nextFunc) == "undefined") nextFunc = null;
    if (typeof(useJSON) == "undefined") useJSON = true;
    if (typeof(args) == "undefined") args = [];
    if (typeof(alwaysCallNextFunc) == "undefined") alwaysCallNextFunc = false;
    if (alwaysCallNextFunc && !nextFunc) {
        alwaysCallNextFunc = false;
    }
    if (toggleButtonID) {
        document.getElementById(toggleButtonID)
                .classList.add("async_operation");
    }
    var async_callback = {
        callback: function(result, data) {
            if (toggleButtonID) {
                //dump("wrapCallbackFunction: "
                //     + methodName
                //     + ", clases: "
                //     + toggleButtonImage.classList
                //     + "\n");
                if (!document) {
                    // stackato window has been closed.
                    return;
                }
                document.getElementById(toggleButtonID)
                        .classList.remove("async_operation");
            } else {
                //dump("wrapCallbackFunction: "
                //     + methodName
                //     + ", toggleButtonID is null"
                //     + "\n");
            }
            if (!alwaysCallNextFunc
                && this_.hasLoggedOut
                && !(methodName == "logout"
                     || (methodName == "runCommand"
                         && (args[0] == "target"
                             || args[0] == "user"
                             || args[0] == "version"
                             || args[0] == "groups")))) {
                return;
            }
            delete this_.pendingRequests[methodName];
            var msgPart = [methodName].concat(args).join(" ")
            if (result == Components.interfaces.koIAsyncCallback.RESULT_ERROR) {
                if (dataHandler.onError) {
                    dataHandler.onError(data && data.stderr);
                } else if (!data || !data.stderr) {
                    ko.dialogs.alert(bundle.formatStringFromName("Stackato X failed", [msgPart], 1));
                } else {
                    ko.dialogs.alert(bundle.formatStringFromName("Stackato X ERROR", [msgPart, data.stderr], 2));
                }
                if (alwaysCallNextFunc) {
                    nextFunc.call(this_);
                }
            } else if (result == Components.interfaces.koIAsyncCallback.RESULT_STOPPED) {
                if (dataHandler.onStopped) {
                    dataHandler.onStopped();
                } else {
                    ko.dialogs.alert(bundle.formatStringFromName("Stackato X operation was stopped", [msgPart], 1));
                }
                if (alwaysCallNextFunc) {
                    nextFunc.call(this_);
                }
            } else if (data.stderr) {
                if (dataHandler.onError) {
                    dataHandler.onError(data.stderr);
                } else {
                    ko.dialogs.alert(bundle.formatStringFromName("Stackato X ERROR", [msgPart, data.stderr], 2));
                }
                if (alwaysCallNextFunc) {
                    nextFunc.call(this_);
                }
            } else {
                //if (args[0] == 'user') {
                //    dump("raw data for s user: " + data.stdout + "\n");
                //}
                var processedData;
                try {
                    processedData = (useJSON
                                     ? JSON.parse(data.stdout)
                                     : data.stdout);
                } catch(ex) {
                    log.exception(ex, "Error in callback for method: "
                                  + methodName
                                  + "/args: "
                                  + args
                                  + ", data.stdout: '"
                                  + data.stdout
                                  + "'");
                    processedData = data.stdout;
                    if (this_.serverRefusedConnectionRE.test(processedData)) {
                        gko.dialogs.alert("Stackato failure", processedData);
                        this_._showLoggedOutFields("", "");
                        return;
                    }
                }
                dataHandler.setData(processedData);
                if (nextFunc) {
                    nextFunc.call(this_);
                }
            }
        }
    };
    if (methodName == "runCommand") {
        if (useJSON && args.indexOf("--json") === -1) {
            args.push("--json");
        }
        return this.pendingRequests[methodName] = this.stackatoService.runCommand(async_callback, args.length, args);
    } else {
        // grumble must be a better way to do this
        switch (args.length) {
            case 0:
            return this.pendingRequests[methodName] = this.stackatoService[methodName](async_callback);
            case 1:
            return this.pendingRequests[methodName] = this.stackatoService[methodName](args[0], async_callback);
            case 2:
            return this.pendingRequests[methodName] = this.stackatoService[methodName](args[0], args[1], async_callback);
            default:
            log.debug("internal error: have to handle " + args.length + " args");
        }
    }
    return null;
};

this.handleFirstTimeRun = function() {
    if (firstTimeRun) {
        var target_textbox = widgets.fields.target_textbox;
        target_textbox.value = bundle.GetStringFromName("Enter a Stackato target endpoint here");
        var func = function(event) {
            target_textbox.value = "";
            target_textbox.removeEventListener("focus", func, false);
            gStackatoPrefs.setBooleanPref("notFirstTime", true);
        };
        target_textbox.addEventListener("focus", func, false);
    }
};

this.sanityCheck_then_getCurrentTarget = function() {
    var this_ = this;
    var handler = {
      onError: function(data) {
            ko.dialogs.alert(bundle.formatStringFromName("sanity_check_and_initialize setData data",
                                                         [(data || "<null>")], 1));
        },
      setData: function(data) {
            if (!data || !/[\d\a-zA-z]\.\d/.test(data)) {
                var prompt = bundle.GetStringFromName("Help Komodo find Stackato");
                var response = bundle.GetStringFromName("Yes");
                var text = bundle.formatStringFromName("Is Komodo currently using a valid version", [(data || "<null>")], 1);
                var title = bundle.GetStringFromName("Problems running Stackato version");
                var res = ko.dialogs.yesNo(prompt, response, text, title);
                if (res == "Yes") {
                    opener.prefs_doGlobalPrefs('stackatoItem');
                }
                return;
            }
            var m = /v?(\d+\.\d+)([\w\d\.]*)/.exec(data);
            this_.clientVersion = m[1];
            this_.clientSubVersion = m[2];
            this_.supportsGroups = this_.versionCheck(1, 2);
            var groupEltNames = ["user1_group_label",
                                 "user1_group_textbox",
                                 "user2_group_label",
                                 "user2_group_textbox"];
            var collapse = !this_.supportsGroups;
            for each (var eltName in groupEltNames) {
                    document.getElementById(eltName).collapsed = collapse;
                }
            this_.getCurrentTarget();
        }
    };
    this.wrapCallbackFunction("runCommand",
                              null,
                              handler, null, false,
                              ["version"]);
};

this.versionCheck = function(majorPart, minorPart, subMinorPart) {
    var versionParts = this.clientVersion.split(".").map(function(p) parseInt(p));
    if (typeof(minorPart) == "undefined") minorPart == 0;
    if (typeof(subMinorPart) == "undefined") subMinorPart == 0;
    if (versionParts[0] < majorPart) {
        return false;
    } else if (versionParts[0] > majorPart
               || (versionParts.length == 1
                   || versionParts[1] > minorPart)) {
        return true;
    } else if (versionParts[1] < minorPart) {
        return false;
    }
    return (versionParts.length == 2
            || versionParts[2] >= subMinorPart);
};

this.getCurrentTarget = function() {
    var this_ = this;
    var handleTarget = {
      onError: function(data) {
            this_.handleFirstTimeRun();
        },
      setData: function(data) {
            var target = data.target;
            if (target) {
                this_.addActiveTarget(target);
                this_._disableChangeTargetButton(true);
                this_._target = target;
                //dump("getCurrentTarget: Got target "
                //     + target
                //     + "\n");
                this_.getUserWithCurrentTarget();
            } else {
                this_._showLoggedOutFields("", "");
                this_.handleFirstTimeRun();
                // Don't get any more data
            }
        }
    };
    this.wrapCallbackFunction("runCommand",
                              "target_label",
                              handleTarget, null, true, /*useJSON*/
                              ["target", "--json"]);
};

this.getUserWithCurrentTarget = function() {
    var this_ = this;
    var handler = {
      setData: function(data) {
            var user = data[0]; //JSON here gives an array.
            //dump("getUserWithCurrentTarget: user: " + user + "\n");
            if (user == "N/A") {
                this_.tryLoggingInWithCredentials();
            } else {
                var newUser, newPassword;
                [newUser, newPassword] = this_.Credentials.credentialsForHostname(this_._target);
                //dump("getUserWithCurrentTarget: current user name: "
                //     + user
                //     + ", newUser"
                //     + newUser
                //     + ", newPassword:"
                //     + newPassword
                //     + "\n");
                this_.user = user;
                this_.password = newPassword;
                this_._updateButtons();
                this_._showLoggedInFields(user, newPassword);
                this_.setupApplicationsTree(true);
            }
        },
      onError: function(msg) {
            ko.dialogs.alert(bundle.formatStringFromName("Stackato getCurrentUser MSG", [msg], 1));
            this_._showLoggedOutFields("", "");
        },
    };
    this.wrapCallbackFunction("runCommand",
                              "target_label",
                              handler, null, true, /*useJSON*/
                              ["user", "--json"]);
};


this.tryLoggingInWithCredentials = function() {
    var newUser, newPassword;
    //dump("In tryLoggingInWithCredentials, current target "
    //     + this._target
    //     + ", known targets: "
    //     + this.Credentials.getTargets().join(", ")
    //     + "\n" );
    [newUser, newPassword] = this.Credentials.credentialsForHostname(this._target);
    //dump("newuser/password for "
    //     + this._target
    //     + ", user: "
    //     + newUser
    //     + ", password: "
    //     + newPassword
    //     + "\n"
    //     );
    if (!newUser) {
        this.hasLoggedOut = true;
        this._showLoggedOutFields("", "");
        this.updateGroupsMenu();
        return;
    }
    var this_ = this;
    this.hasLoggedOut = false;
    var handler = {
      onError: function(msg) {
            this_.user = "";
            this_.password = "";
            this_.hasLoggedOut = true;
            this_._showLoggedOutFields(newUser, newPassword);
            this.updateGroupsMenu();
            ko.dialogs.alert(bundle.formatStringFromName("Stackato X ERROR", ["login", msg], 2));
        },
      setData: function(data) {
            // Hardwired string from Stackato client, do not i18nize
            if (data && data.indexOf("Successfully logged into") == 0) {
                this_.user = newUser;
                this_.password = newPassword;
                this_._showLoggedInFields(this_.user, this_.password);
                this_._updateButtons();
                this_.setupApplicationsTree(true);
            } else {
                // Hardwired string from Stackato client, do not i18nize
                if (data && data.indexOf("Problem with login, invalid account or password") == 0) {
                    ko.dialogs.alert(data);
                }
                this_.hasLoggedOut = true;
                this_._updateButtons();
                this_.updateGroupsMenu();
                this_._showLoggedOutFields(newUser, newPassword);
            }
        }
    };
    this.wrapCallbackFunction("login", "user1_label",
                              handler,
                              null, false, [newUser, newPassword]);
};

this.setupApplicationsTree = function(doFullCallback) {
    var view;
    if (widgets.views.mainTree) {
        view = widgets.views.mainTree;
    } else {
        view = widgets.views.mainTree = new ko.stackato.trees.ApplicationsTree(gStackatoPrefs);
        widgets.trees.mainTree.treeBoxObject.view = view;
    }
    var this_ = this;
    var nextCallback = (doFullCallback
                        ? function() {this_.setupServicesTree();}
                        : null);
    var callback = (gStackatoPrefs.hasBooleanPref("showEnvironment")
                    && gStackatoPrefs.getBooleanPref("showEnvironment")
                    ? function() {
                        document.getElementById("maintree_show_env").checked = true;
                        this_.showEnvironmentVariables = true;
                        this_.doToggleShowEnvironment(true, nextCallback);
                    } : nextCallback);
    this.wrapCallbackFunction("getApplications",
                              "applications_button",
                              view,
                              callback);
};

this.setupServicesTree = function(inStartup) {
    var view = widgets.views.servicesProvisionedTree = this.servicesTreeManager.servicesProvisionedTree;
    widgets.trees.servicesProvisionedTree.treeBoxObject.view = view;
    
    var view2 = widgets.views.servicesSystemTree = this.servicesTreeManager.servicesSystemTree;
    widgets.trees.servicesSystemTree.treeBoxObject.view = view2;
    var this_ = this;
    var callback = function() {
        this_.provisionedServiceNames = view.getNames();
        this_.systemServiceNames = view2.getNames();
        this_.setupFrameworksTree();
    };
    this.wrapCallbackFunction("getServices",
                              "provisioned_services_button",
                              this.servicesTreeManager,
                              callback);
};

this.refreshProvisionedServicesTree = function(outer_callback, iconID) {
    var this_ = this;
    var callback = function() {
        this_.provisionedServiceNames =
                widgets.views.servicesProvisionedTree.getNames();
        if (outer_callback) {
            outer_callback();
        }
    };
    this.wrapCallbackFunction("getServices",
                              iconID,
                              this.servicesTreeManager,
                              callback);
};

this.setupFrameworksTree = function() {
    var view = widgets.views.frameworksTree = new ko.stackato.trees.FrameworksTree();
    widgets.trees.frameworksTree.treeBoxObject.view = view;
    var this_ = this;
    var callback = function() {
        this_.frameworkNames = view.getNames();
        this_.setupRuntimesTree();
    };
    this.wrapCallbackFunction("getFrameworks",
                              "provisioned_services_button",
                              view,
                              callback);
};

this.setupRuntimesTree = function() {
    var view = widgets.views.runtimesTree = new ko.stackato.trees.RuntimesTree();
    widgets.trees.runtimesTree.treeBoxObject.view = view;
    var this_ = this;
    var callback = function() {
        this_.runtimeNames = view.getRuntimeNames();
        this_.setupTargetsTree();
    };
    this.wrapCallbackFunction("getRuntimes",
                              "provisioned_services_button",
                              view,
                              callback);
};

this.arrayUnion = function(a1, a2) {
    // Preserve the order of the first set, then add on any new members in the second set
    return a1.concat(this.arrayDifference(a2, a1));
    //return a1.concat(a2.filter(function(x) !~a1.indexOf(x)));
}

this.arrayDifference = function(a1, a2) {
    // Return any items that are in a1 but not a2
    return a1.filter(function(x) !~a2.indexOf(x));
}

this._getTargetsUpdateTargetMenu = function(getGroups) {
    var view = widgets.views.targetsTree;
    var discoveredTargetNames = view ? view.getTargetNames() : [];
    var credentialTargetNames = this.Credentials.getTargets();
    var mruTargetNames = gko.mru.getAll("mruStackatoTargetList");
    mruTargetNames.reverse();
    var targetNames = this.arrayUnion(mruTargetNames, discoveredTargetNames);
    // remove any credential names that aren't in targetNames
    var oldCredentialNames = this.arrayDifference(credentialTargetNames, targetNames);
    for each (var name in oldCredentialNames) {
            this.Credentials.removeEntry(name);
        };
    this.targetNames = targetNames;
    g_finishedInit = true;
    this._updateButtons();
    this.updateTargetsMenu(this.targetNames, /*getGroups=*/true);
};

this.setupTargetsTree = function() {
    var view = widgets.views.targetsTree = new ko.stackato.trees.TargetsTree();
    widgets.trees.targetsTree.treeBoxObject.view = view;
    var callback = function() {
        this._getTargetsUpdateTargetMenu(/*getGroups=*/true);
    }.bind(this);
    this.wrapCallbackFunction("getTargets",
                              "provisioned_services_button",
                              view,
                              callback);
};

this.updateTargetsMenu = function(names, getGroups) {
    var menuitem, menupopup = document.getElementById("target_textbox_menupopup");
    while (menupopup.firstChild) {
        menupopup.removeChild(menupopup.firstChild);
    }
    for each (var name in names) {
        menuitem = document.createElement("menuitem");
        menuitem.setAttribute("label", name);
        menupopup.appendChild(menuitem);
    }
    if (this.supportsGroups && getGroups) {
        this.getGroupNames();
    }
};

this.getGroupNames = function() {
    var this_ = this;
    var handler = {
        onError: function(data) {
            if (data.indexOf("does not support groups") !== -1) {
                this_.updateGroupsMenuForIndex([], 1); // logged in
                this_.updateGroupsMenuForIndex([], 2);           // logged out
            } else {
                this_.updateGroupsMenu();
            }
        },
        setData: function(data) {
            this_.groupNamesByTarget[this_._target] = data;
            this_.updateGroupsMenu();
        }
    };
    this.wrapCallbackFunction("runCommand",
                              "target_label",
                              handler,
                              null,
                              /*useJSON=*/true,
                              /*args=*/['groups']
                              );
};

this.updateGroupsMenu = function() {
    var all_gnames = [];
    var user_specific_gnames = [];
    if (this.supportsGroups) {
        if (this._target in this.groupNamesByTarget) {
            var groupInfo = this.groupNamesByTarget[this._target];
            for (var p in groupInfo) {
                all_gnames.push(p);
                if (!this.hasLoggedOut && groupInfo[p].indexOf(this.user) !== -1) {
                    user_specific_gnames.push(p);
                }
            }
        }
        all_gnames.sort(); //TODO: ignore case
        user_specific_gnames.sort(); //TODO: ignore case
    }
    this.updateGroupsMenuForIndex(user_specific_gnames, 1); // logged in
    this.updateGroupsMenuForIndex(all_gnames, 2);           // logged out
};

this.updateGroupsMenuForIndex = function(gnames, idx) {
    var menulist = document.getElementById("user" + idx + "_group_textbox");
    if (!gnames.length) {
        menulist.disabled = true;
        return;
    }
    menulist.disabled = false;
    var sep = document.getElementById("user" + idx + "_group_popup_separator");
    var popup = sep;
    var parentNode = popup.parentNode;
    var nextSib = popup.nextSibling;
    while (nextSib) {
        popup = nextSib;
        nextSib = popup.nextSibling;
        parentNode.removeChild(popup);
    }
    var menupopup = document.getElementById("user" + idx + "_group_textbox_menupopup");
    var menuitem;
    for each (var name in gnames) {
        menuitem = document.createElement("menuitem");
        menuitem.setAttribute("label", name);
        menupopup.appendChild(menuitem);
    }
};

this.switchGroup = function(sender) {
    if (this.hasLoggedOut) {
        //dump("not logged in...\n");
        return;
    }
    if (sender.selectedIndex === 0) {
        this.switchToGroup(null);
    } else {
        var gname = sender.selectedItem.label;
        if (gname) {
            this.switchToGroup(gname);
        }
    }
};

this.switchToGroup = function(gname) {
    var this_ = this;
    var handler = {
        onError: function(data) {
            //dump("group " + gname + " => error: " + data + "\n");
        },
        setData: function(data) {
            //dump("group " + gname + "; output: " + data + "\n");
            this_.refreshAppTree();
        }
    };
    if (!gname) {
        gname = this_.versionCheck(1, 3) ? "--reset" : "reset";
    }
    this.wrapCallbackFunction("runCommand",
                              "user2_group_label",
                              handler,
                              null,
                              /*useJSON=*/false,
                              /*args=*/['group', gname]
                              );
};

this._addNewItem = function(menupopup, newLabel) {
    if (!menupopup.getElementsByAttribute("label", newLabel).length) {
        var menuitem = document.createElement("menuitem");
        menuitem.setAttribute("label", newLabel);
        menupopup.appendChild(menuitem);
    }
};

this.addActiveTarget = function(targetEndPoint) {
    this._addNewItem(document.getElementById("target_textbox_menupopup"),
                      targetEndPoint);
    widgets.fields.target_textbox.label = targetEndPoint;
};

this.refreshAppTree = function() {
    this.setupApplicationsTree(false);
};

this.clearTrees = function() {
    for each (var view in widgets.views) {
            if (view.clear) {
                view.clear();
            }
        }
};

// Selection handlers

this.mainTree_OnSelect = function() {
    this.updateStackatoToolbar();
};

this.mainTree_onDoubleClick = function() {
    // There's nothing to do
};

this.mainTree_onKeyPress = function(event) {
    var t = event.originalTarget;
    if (t.localName != "treechildren" && t.localName != 'tree') {
        return false;
    }
    // Special-case some commands, and then look at the keybinding set
    // to determine a command to do.
    if (!(event.shiftKey || event.ctrlKey || event.altKey)) {
        if (this.arrowKeys.indexOf(event.keyCode) >= 0) {
            // Nothing to do but squelch the keycode
            this.updateStackatoToolbar();
        } else if (event.keyCode == event.DOM_VK_RETURN) {
            // What to do?
        } else if (event.keyCode == event.DOM_VK_DELETE) {
            this._application_command(event, "delete", true);
        }
    }
    return true;
};

this.servicesSystemTree_OnSelect = function() {
    //log.debug(">> servicesSystemTree_OnSelect");
};

this.servicesProvisionedTree_OnSelect = function() {
    //log.debug(">> servicesProvisionedTree_OnSelect");
};

this.frameworksTree_OnSelect = function() {
    //log.debug(">> frameworksTree_OnSelect");
};

this.runtimesTree_OnSelect = function() {
    //log.debug(">> runtimesTree_OnSelect");
};

this.targetsTree_OnSelect = function() {
    //log.debug(">> targetsTree_OnSelect");
};

this.onUnload = function() {
    try {
        // endSession is used to ensure the terminal handler does not try to
        // continue to use scintilla or the view elements.
        gStackatoPrefs.setStringPref("groupNamesByTarget",
                                     JSON.stringify(this.groupNamesByTarget));
        g_shuttingDown = true;
        terminalView.endSession();
        g_terminalHandler.endSession();
        // This ensures the scintilla view is properly cleaned up.
        terminalView.close();
        scintillaOverlayOnUnload();
    } catch(ex) {
        log.exception(ex);
    }
};

///////////////////////////////////////////////////////////////////////
// Context Menu Handlers

this.getStackatoEnv = function(obj) {
    // obj.stackato and obj.path will be quoted if necessary
    // obj.cwd won't be, since it's usually passed as a separate arg.
    var prefs = gko.prefs;
    try {
        obj.stackato = prefs.getStringPref("stackato.location");
    } catch(ex) {
        obj.stackato = null;
    }
    if (!obj.stackato) {
        var prompt = bundle.GetStringFromName("Komodo needs to know where the Stackato executable is located");
        var title = bundle.GetStringFromName("Stackato Configuration");
        var defaultResponse = bundle.GetStringFromName("No");
        var response = gko.dialogs.yesNo(prompt, defaultResponse, null, title);
        if (response == bundle.GetStringFromName('Yes')) {
            opener.prefs_doGlobalPrefs('stackatoItem');
            return;
        }
    }
    obj.stackato = this.quote_if_needed(obj.stackato);
    var sysUtilsSvc = Components.classes['@activestate.com/koSysUtils;1'].getService(Components.interfaces.koISysUtils);
    var osSvc = Components.classes["@activestate.com/koOs;1"].getService(Components.interfaces.koIOs);
    var osPathSvc = Components.classes["@activestate.com/koOsPath;1"].getService(Components.interfaces.koIOsPath);
    var environSvc = Components.classes["@activestate.com/koUserEnviron;1"].getService(Components.interfaces.koIUserEnviron);
    var path = environSvc.get("PATH");
    obj.path = this.quote_if_needed([osPathSvc.dirname(obj.stackato), path].join(osSvc.pathsep));
    try {
        var file = gko.views.manager.currentView.koDoc.file;
        if (file.scheme == "file") {
            obj.cwd = file.dirName;
        } else {
            obj.cwd = null;
        }
    } catch(ex2) {
        log.exception(ex2, "error getting current view dir:");
    }
};

this.quote_if_needed = function quote_if_needed(s) {
    var s1;
    if (/[^\w.:=\-\"\'\\\/]/.test(s)) {
        s1 = '"' + s + '"';
    } else {
        s1 = s;
    }
    return s1;
};

this.getSelectionInfo = function(view, index) {
    var row;
    if (index < 0 || index >= view.rowCount) {
        row = null;
    } else {
        var thisRow = view.getRow(index);
        var mainRow = thisRow.fields.name ? thisRow : view.getMainRow(index);
        row = {
          name: mainRow.fields.name,
          health: mainRow.fields.health,
          num_instances: mainRow.fields.num_instances,
          serviceName: thisRow.fields.serviceName,
          hasService: !!mainRow.fields.serviceName,
          url: thisRow.fields.url,
          env_name: thisRow.fields.env_name,
        };
    }
    return {
      empty: !mainRow,
      fields: row,
      loggedOut: widgets.fields["user_logged_out"].getAttribute("hidden") != "true",
      showingEnvironmentVariables: this.showEnvironmentVariables
    };
};

this.updateStackatoToolbar = function() {
    var view = widgets.views.mainTree;
    var index = view.selection.currentIndex;
    var row;
    var selectionInfo = this.getSelectionInfo(view, index);
    // This should just work.  All we care about is enabling/disabling these.
    var nodeParent = document.getElementById("stackato_apps_toolbar");
    var childNodes = nodeParent.childNodes;
    for (var i = childNodes.length - 1; i >= 0; --i) {
        this._doMainTreeContextMenu(childNodes[i], selectionInfo);
    }
};

this.initMainTreeContextMenu = function(event, menupopup) {
    var clickedNodeId = event.explicitOriginalTarget.id;
    if (clickedNodeId == "mtcm_bindService_popup") {
        return true;
    } else if (clickedNodeId != "mainTree_treechildren") {
        log.debug("Rejecting node " + clickedNodeId);
        return false;
    }
    var row = {};
    widgets.trees.mainTree.treeBoxObject.getCellAt(event.pageX, event.pageY, row, {},{});
    var index = row.value;
    var selectionInfo = this.getSelectionInfo(widgets.views.mainTree, index);
    var childNodes = menupopup.childNodes;
    for (var i = childNodes.length - 1; i >= 0; --i) {
        this._doMainTreeContextMenu(childNodes[i], selectionInfo);
    }
    return true;
};

this._doMainTreeContextMenu = function(menuNode, selectionInfo) {
    var hideIf = menuNode.getAttribute('hideIf');
    var ptn = /^field:(.*?)(?:=(.*))?$/;
    var m, fieldName, fieldValue;
    var fields = selectionInfo.fields;
    if (hideIf && fields) {
        m = ptn.exec(hideIf);
        if (m) {
            fieldName = m[1];
            fieldValue = m[2] || '';
            if (fields[fieldName]) {
                if (fieldValue) {
                    if (fieldValue == fields[fieldName]) {
                        menuNode.setAttribute('collapsed', true);
                        return; // No need to do anything else
                    }
                } else {
                    menuNode.setAttribute('collapsed', true);
                    return; // No need to do anything else
                }
            }
        }
    }
    var hideUnless = menuNode.getAttribute('hideUnless');
    if (hideUnless == "showingEnvironmentVariables"
        && !selectionInfo.showingEnvironmentVariables) {
        menuNode.setAttribute('collapsed', true);
        return; // No need to do anything else
    }
    menuNode.removeAttribute('collapsed');
    var disableNode = false;
    var disableIf = menuNode.getAttribute('disableIf');
    if (disableIf) {
        for each (var disableIfVal in disableIf.split(';')) {
                if (disableIfVal == 'empty') {
                    if (!selectionInfo.fields) {
                        disableNode = true;
                        break;
                    }
                } else if (disableIfVal == 'loggedOut') {
                    if (selectionInfo.loggedOut) {
                        disableNode = true;
                        break;
                    }
                } else if (disableIfVal == "noBoundApp") {
                    if (!this.getAppForServiceName(fields.serviceName)) {
                        disableNode = true;
                        break;
                    }
                } else if (disableIfVal == "hasService") {
                    if (fields.hasService) {
                        disableNode = true;
                        break;
                    }
                } else if (selectionInfo.fields) {
                    m = ptn.exec(disableIfVal);
                    if (m) {
                        fieldName = m[1];
                        fieldValue = m[2] || '';
                        if (fields[fieldName]) {
                            if (fieldValue) {
                                if (fieldValue == fields[fieldName]) {
                                    disableNode = true;
                                }
                            } else {
                                disableNode = true;
                            }
                        }
                    }
                }
            }
    }
    if (!disableNode) {
        var disableUnless = menuNode.getAttribute('disableUnless');
        if (disableUnless) {
            if (disableUnless == 'empty') {
                if (selectionInfo.fields) {
                    var disableNode = true;
                }
            } else if (selectionInfo.fields) {
                m = ptn.exec(disableUnless);
                if (m) {
                    fieldName = m[1];
                    if (!fields[fieldName]) {
                        disableNode = true;
                    } else {
                        fieldValue = m[2] || '';
                        if (fieldValue && fieldValue != fields[fieldName]) {
                            disableNode = true;
                        }
                    }
                }
            } else {
                disableNode = true;
            }
        }
    }
    if (disableNode) {
        menuNode.setAttribute('disabled', true);
    } else {
        menuNode.removeAttribute('disabled');
    }
    this._adjustTooltiptextAttribute(menuNode, disableNode);
};

this._adjustTooltiptextAttribute = function(menuNode, disableNode) {
    /**
     * If this node has a disabled_tooltiptext attr, and we're disabling it,
     * set the tooltiptext to it to explain why.
     * Of less obvious use, do same with enabled_tooltiptext for enabled nodes.
     */
    var hasEnabledAttr = menuNode.hasAttribute("enabled_tooltiptext");
    if (disableNode) {
        if (!hasEnabledAttr && menuNode.hasAttribute("tooltiptext")) {
            menuNode.setAttribute("enabled_tooltiptext",
                                  menuNode.getAttribute("tooltiptext"));
        }
        if (menuNode.hasAttribute("disabled_tooltiptext")) {
            menuNode.setAttribute("tooltiptext",
                                  menuNode.getAttribute("disabled_tooltiptext"));
        }
        // Otherwise, just leave the attr as is.
    } else if (hasEnabledAttr) {
        menuNode.setAttribute("tooltiptext",
                              menuNode.getAttribute("enabled_tooltiptext"));
    }
}

this.initProvisionedServicesContextMenu = function(event, menupopup) {
    var row = {};
    widgets.trees.servicesProvisionedTree.treeBoxObject.getCellAt(event.pageX, event.pageY, row, {},{});
    var index = row.value;
    var view = widgets.views.servicesProvisionedTree;
    var selectedRow = ((index < 0 || index > view.rowCount)
                       ? null : view.getRow(index));
    var selectionInfo = {
      empty: !selectedRow,
      loggedOut: widgets.fields["user_logged_out"].getAttribute("hidden") != "true",
      fields: {}
    };
    if (selectedRow) {
        selectionInfo.fields.serviceName = view.getNameAtIndex(index);
    }
    var childNodes = menupopup.childNodes;
    for (var i = childNodes.length - 1; i >= 0; --i) {
        this._doMainTreeContextMenu(childNodes[i], selectionInfo);
    }
    return true;
};

this._applicationCurrentRow = function(event) {
    return widgets.views.mainTree.selection.currentIndex;
};

this._updateApplicationsTable = function(nextFunc) {
    if (typeof(nextFunc) == "undefined") nextFunc = null;
    this.wrapCallbackFunction("getApplications",
                              "applications_button",
                              widgets.views.mainTree,
                              nextFunc);
};

this.internAppNamePrefset = function(appName) {
    var outerAppPrefs = gStackatoPrefs.getPref("apps");
    var appPrefs;
    if (outerAppPrefs.hasPref(appName)) {
        appPrefs = outerAppPrefs.getPref(appName);
    } else {
        appPrefs = Components.classes["@activestate.com/koPreferenceSet;1"].createInstance();
        outerAppPrefs.setPref(appName, appPrefs);
    }
    return appPrefs;
}

this._getMainRowAndAppName = function(event) {
    var index = this._applicationCurrentRow(event);
    if (index < 0) return [null, null];
    var row = widgets.views.mainTree.getMainRow(index);
    if (!row) {
        log.debug("No row for this item");
        return [row, null];
    }
    var appName = row.fields.name;
    if (!appName) {
        log.debug("No appName for row " + index);
    }
    return [row, appName];
};

this.application_browseCode = function(event) {
    var row, appName;
    [row, appName] = this._getMainRowAndAppName(event);
    if (!row || !appName) return;
    var appPrefs = this.internAppNamePrefset(appName);
    var pwd = null;
    if (appPrefs && appPrefs.hasPref("pwd")) {
        pwd = appPrefs.getStringPref("pwd");
    }
    if (!pwd) {
        pwd =  gko.filepicker.getFolder(null, bundle.GetStringFromName("Where is this project located"));
        if (pwd) {
            appPrefs.setStringPref("pwd", pwd);
        }
    }
    if (!pwd) {
        return;
    }
    gko.views.manager.notify_visited_directory(pwd);
};

this.application_reset_directory = function(event) {
    var appName = this._getMainRowAndAppName(event)[1];
    if (!appName) return;
    var appPrefs = this.internAppNamePrefset(appName);
    if (!appPrefs) {
        ko.dialogs.alert("Komodo/Stackato: Internal Error: can't find prefs for application \"" + appName + '"');
        return;
    }
    var pwd = (appPrefs.hasPref("pwd") ? appPrefs.getStringPref("pwd") : null);
    var newPwd = gko.filepicker.getFolder(pwd, bundle.GetStringFromName("Where is this project located"));
    if (newPwd) {
        appPrefs.setStringPref('pwd', newPwd);
    }
}

this.application_update = function(event) {
    var row, appName;
    [row, appName] = this._getMainRowAndAppName(event);
    if (!row || !appName) return;
    var data = row.data;
    var pwd = null;
    var window;
    var appPrefs = this.internAppNamePrefset(appName);
    try {
        pwd = appPrefs.getStringPref("pwd");
    } catch(ex) {
    }
    if (!pwd) {
        if (data.pwd) {
            pwd = data.pwd;
        } else {
            var project = gko.projects.manager.currentProject;
            if (project) {
                pwd = project.getFile().dirName;
            }
            pwd =  gko.filepicker.getFolder(pwd, bundle.GetStringFromName("Where is this project located"));
            if (!pwd) {
                return;
            }
            data.pwd = pwd;
        }
        appPrefs.setStringPref("pwd", pwd);
    }
    
    var command = "update";
    var args = [command, appName, "--path", this.quote_if_needed(pwd), "-n"];
    var terminationCallback = function(retval) {
        log.debug("cmd <" + command + "> finished => " + retval);
        ko.stackato._updateApplicationsTable();
    };
    this._clearTerminal = true;
    this.doApplicationCommand(args, terminationCallback);
};

this._application_command = function(event, commandName, prompt) {
    var appName = this._getMainRowAndAppName(event)[1];
    if (!appName) return;
    var actualPrompt = (prompt
                        ? bundle.formatStringFromName("X application Y", [commandName, appName], 2)
                        : null);
    var this_ = this;
    var terminationCallback = function(retval) {
        log.debug("restart finished => " + retval);
        this_._updateApplicationsTable();
    };
    this._clearTerminal = true;
    this.doApplicationCommand([commandName, appName], terminationCallback,
                              actualPrompt, "applications_button");
}

this.application_restart = function(event) {
    this._application_command(event, "restart");
};

this.application_start = function(event) {
    this._application_command(event, "start");
};

this.application_stop = function(event) {
    this._application_command(event, "stop");
};

this.application_rename = function(event) {
    var appName = this._getMainRowAndAppName(event)[1];
    if (!appName) return;
    var prompt = bundle.GetStringFromName("New Application Name");
    var label = bundle.GetStringFromName("Name Colon");
    var value = appName;
    var title = prompt;
    var newAppName = ko.dialogs.prompt(prompt, label, value, title);
    if (!newAppName || appName == newAppName) {
        return;
    }
    if (widgets.views.mainTree.getNames().indexOf(newAppName) !== -1) {
        gko.statusBar.AddMessage(bundle.formatStringFromName("Stackato name in use X", [newAppName], 1),
                                 bundle.GetStringFromName("Stackato"),
                                 3000, true);
        _stackatoWindow.focus();
        return;
    }
    var this_ = this;
    var terminationCallback = function(retval) {
        log.debug("rename finished => " + retval);
        this_._updateApplicationsTable();
    };
    this._clearTerminal = true;
    this.doApplicationCommand(["rename", appName, newAppName],
                              terminationCallback,
                              null, "applications_button");
};

this.application_delete = function(event) {
    // Verify that there's no service attached.
    this._application_command(event, "delete", true);
};

this.application_refresh = function() {
    var this_ = this;
    var nextFunc = function() {
        this_._updateProvisionedServicesTable();
    };
    this._updateApplicationsTable(nextFunc);
};

this.application_add = function(event) {
    var getNewAppFieldResults = {};
    var argumentsObj = {gko:gko, 'window':gWindow, ko:ko,
                        stackato: this,
                        currentTarget: this._target,
                        results:getNewAppFieldResults};
    var res = ko.windowManager.openOrFocusDialog(
        "chrome://stackatotools/content/stackatoNewApp.xul",
        "komodo_stackato",
        "chrome,all,close=yes,resizable,dependent=no,modal=yes",
        argumentsObj);
    if (!res) {
        // canceled out
        return;
    }
    var this_ = this;
    var terminationCallbackRebuildTable = function(retval) {
        try {
        if (retval) {
            return;
        }
        this_._updateApplicationsTable();
        } catch(ex) {
            log.debug("terminationCallbackRebuildTable: " + ex );
        }
    };
    var terminationCallbackStartService = function(retval) {
        try {
        if (retval) return;
        var args = ['start', getNewAppFieldResults.appname];
        this_.doApplicationCommand(args, terminationCallbackRebuildTable);
        } catch(ex) {
            log.exception(ex, "terminationCallbackStartService: ");
        }
    };
    var terminationCallbackBindService = function(retval) {
        try {
        if (retval) return;
        if (getNewAppFieldResults.appname
            && getNewAppFieldResults.path) {
            var appPrefs = this_.internAppNamePrefset(getNewAppFieldResults.appname);
            appPrefs.setStringPref("pwd", getNewAppFieldResults.path);
        }
        // Update the prefs before doing anything else.
        if (getNewAppFieldResults.provisionedService) {
            var args = ['bind-service',
                        getNewAppFieldResults.provisionedService,
                        getNewAppFieldResults.appname];
            this_.doApplicationCommand(args, terminationCallbackStartService);
        } else {
            terminationCallbackStartService(0);
        }
        } catch(ex) {
            log.exception(ex, "terminationCallbackBindService:");
        }
    };
    var args = ['push'];
    // Names:
    // appname path url mem instances runtime startImmediately
    var required_names = ['appname', 'path', 'url', 'mem'];
    for each (var name in required_names) {
        if (!getNewAppFieldResults[name]) {
            log.debug("results." + name + " not specified");
            return;
        }
    }
    args.push(getNewAppFieldResults.appname,
              "--path", getNewAppFieldResults.path,
              "--url",  getNewAppFieldResults.url);
    if (getNewAppFieldResults.instances) {
        args.push("--instances", getNewAppFieldResults.instances);
    }
    if (getNewAppFieldResults.runtime) {
        args.push("--runtime", getNewAppFieldResults.runtime);
    }
    if (getNewAppFieldResults.framework) {
        args.push("--framework", getNewAppFieldResults.framework);
    }
    if (!getNewAppFieldResults.startImmediately) {
        args.push("--no-start");
    }
    this._clearTerminal = true;
    this.doApplicationCommand(args, terminationCallbackBindService,
                              null, "applications_button");
};

this.application_mapUrl = function(event) {
    var appName = this._getMainRowAndAppName(event)[1];
    if (!appName) return;
    var urls = widgets.views.mainTree.getURLsForApp(appName);
    var prompt = bundle.GetStringFromName("New URL To Add");
    var label = bundle.GetStringFromName("URLColon");
    var value = urls.length ? urls[urls.length - 1] : "";
    var title = prompt;
    var newURL = ko.dialogs.prompt(prompt, label, value, title);
    if (!newURL) {
        return;
    } else if (widgets.views.mainTree.getURLs().indexOf(newURL) !== -1) {
        gko.statusBar.AddMessage(bundle.formatStringFromName("URL is already in use X", [newURL], 1),
                                 bundle.GetStringFromName("Stackato"),
                                 3000, true);
        _stackatoWindow.focus();
        return;
    }
    var this_ = this;
    var terminationCallback = function(retval) {
        log.debug("mapURL finished => " + retval);
        this_._updateApplicationsTable();
    };
    this._clearTerminal = true;
    this.doApplicationCommand(["map", appName, newURL],
                              terminationCallback,
                              null, "applications_button");
};

this.application_unmapUrl = function(event) {
    var index = this._applicationCurrentRow(event);
    if (index < 0) return;
    var thisRow = widgets.views.mainTree.getRow(index);
    var mainRow = thisRow.fields.name ? thisRow : widgets.views.mainTree.getMainRow(index);
    var appName = mainRow.fields.name;
    var url = thisRow.fields.url;
    if (!appName || !url) {
        dump("No "
             + (appName ? "url" : "appname")
             + " for row " + index + "\n");
        return;
    }
    var cmd = "unmap";
    var this_ = this;
    var terminationCallback = function(retval) {
        log.debug(cmd + " finished => " + retval);
        this_._updateApplicationsTable();
    };
    var prompt = bundle.formatStringFromName("unmap URL X", [url], 1);
    this._clearTerminal = true;
    this.doApplicationCommand([cmd, appName, url],
                              terminationCallback,
                              prompt, "applications_button");
};

this.application_changeInstances = function(event) {
    var mainRow, appName;
    [mainRow, appName] = this._getMainRowAndAppName(event);
    if (!mainRow || !appName) return;
    var numInstances = mainRow.fields.num_instances;
    var prompt = bundle.GetStringFromName("Number of Instances To Run");
    var label = bundle.GetStringFromName("Num Instances");
    var value = numInstances;
    var title = prompt;
    var newNumInstances = ko.dialogs.prompt(prompt, label, value, title);
    if (!newNumInstances || newNumInstances == numInstances) {
        return;
    } else if (!/^\d+$/.test(newNumInstances)) {
        gko.statusBar.AddMessage(bundle.formatStringFromName("Instances must be a number, rejecting X", [newNumInstances], 1),
                                 bundle.GetStringFromName("Stackato"),
                                 3000, true);
        _stackatoWindow.focus();
        return;
    }
    var this_ = this;
    var terminationCallback = function(retval) {
        log.debug("instances finished => " + retval);
        this_._updateApplicationsTable();
    };
    this._clearTerminal = true;
    this.doApplicationCommand(["instances", appName, newNumInstances],
                              terminationCallback,
                              null, "applications_button");
};

const mem1K = 1024;
const mem1M = mem1K * 1024;
const mem1G = mem1M * 1024;
this.application_changeMemory = function(event) {
    var appName = this._getMainRowAndAppName(event)[1];
    if (!appName) return;
    var this_ = this;
    var handler = {
        setData: function(data) {
            try {
                var memUsedLabel;
                var mem_quota_bytes = data[0].stats.mem_quota;
                if (mem_quota_bytes >= mem1G) {
                    memUsedLabel = Math.round(mem_quota_bytes / mem1G) + "G";
                } else if (mem_quota_bytes >= mem1M) {
                    memUsedLabel = Math.round(mem_quota_bytes / mem1M) + "M";
                } else if (mem_quota_bytes >= mem1K) {
                    memUsedLabel = Math.round(mem_quota_bytes / mem1K) + "K";
                } else {
                    memUsedLabel = mem_quota_bytes + "B";
                }
                var results = {memoryLimit: memUsedLabel};
                var res = ko.windowManager.openOrFocusDialog(
                    "chrome://stackatotools/content/stackatoSelectMemory.xul",
                    "komodo_stackato",
                    "chrome,all,close=yes,resizable,dependent=no,modal=yes",
                   results);
                if (!res || !results.newMemoryLimit || results.newMemoryLimit == results.memoryLimit) {
                    // canceled out
                    return;
                }
                this_.doApplicationCommand(["mem", appName, results.newMemoryLimit],
                                           null,
                                           null, "applications_button");
            } catch(ex) {
                gko.dialogs.alert("Komodo/Stackato internal error: " + ex);
            }
        }
    }
    this.wrapCallbackFunction("runCommand",
                              "applications_button",
                              handler, null, true, /*useJSON*/
                              ["stats", appName, "--json"]);
};

this.application_addEnvVar = function(event) {
    var appName = this._getMainRowAndAppName(event)[1];
    if (!appName) return;
    var prompt = bundle.GetStringFromName("New environment variable__use name-value format");
    var label = bundle.GetStringFromName("Variable and value");
    var value = "";
    var title = bundle.GetStringFromName("Add New Environment Variable");
    var res = ko.dialogs.prompt(prompt, label, value, title);
    if (!res) {
        return;
    }
    if (res.indexOf('=') == -1) {
        res += "=";
    }
    var this_ = this;
    var terminationCallback = function(retval) {
        log.debug("env_add finished => " + retval);
        this_.getAndUpdateEnvironmentVarsForAppname(widgets.views.mainTree, appName, null);
    };
    this._clearTerminal = true;
    this.doApplicationCommand(["env-add", appName, res],
                              terminationCallback,
                              null, "applications_button");
};

this.application_removeEnvVar = function(event) {
    var index = this._applicationCurrentRow(event);
    if (index < 0) return;
    var view = widgets.views.mainTree;
    var thisRow = view.getRow(index);
    var mainRow = view.getMainRow(index);
    var appName = mainRow.fields.name;
    if (!appName) {
        dump("No appname for row " + index + "\n");
        return;
    }
    var envVarName = thisRow.fields.env_name;
    if (!envVarName) {
        log.debug("No env var for row " + index);
        return;
    }
    var this_ = this;
    var terminationCallback = function(retval) {
        log.debug("env_del finished => " + retval);
        this_.getAndUpdateEnvironmentVarsForAppname(view, appName, null);
    };
    var prompt = bundle.formatStringFromName('drop environment variable X',
                                             [envVarName], 1);
    this._clearTerminal = true;
    this.doApplicationCommand(["env-del", appName, envVarName],
                              terminationCallback,
                              prompt, "applications_button");
};

this.bindService_show_services = function(event, menupopup) {
    while (menupopup.firstChild) {
        menupopup.removeChild(menupopup.firstChild);
    }
    var index = this._applicationCurrentRow(event);
    if (index < 0) return false;
    var appName = widgets.views.mainTree.getAppNameForRow(index);
    if (!appName) {
        log.debug("No appname for row " + index);
        return false;
    }
    var currentServiceNames = widgets.views.mainTree.getServicesForApp(appName);
    var menuitem, handler;
    for each (var name in this.provisionedServiceNames) {
            menuitem = document.createElement("menuitem");
            menuitem.setAttribute("label", name);
            menuitem.setAttribute("id", "bindService_" + name);
            if (currentServiceNames.indexOf(name) !== -1) {
                menuitem.setAttribute("disabled", "true");
            } else {
                handler = ("ko.stackato.application_bindService('"
                           + appName
                           + "', '"
                           + name
                           + "');");
                menuitem.setAttribute("oncommand", handler);
            }
            menupopup.appendChild(menuitem);
        }
    return true;
};

this.application_bindService = function(appName, serviceName) {
    var this_ = this;
    var terminationCallback = function(retval) {
        log.debug("bind-service finished => " + retval);
        this_._updateApplicationsTable();
    };
    this._clearTerminal = true;
    this.doApplicationCommand(["bind-service", serviceName, appName],
                              terminationCallback,
                              null, "applications_button");
};

this.application_unbindService = function(event) {
    var index = this._applicationCurrentRow(event);
    if (index < 0) return;
    var thisRow = widgets.views.mainTree.getRow(index);
    var mainRow = thisRow.fields.name ? thisRow : widgets.views.mainTree.getMainRow(index);
    var appName = mainRow.fields.name;
    var serviceName = thisRow.fields.serviceName;
    if (!appName || !serviceName) {
        dump("No "
             + (appName ? "serviceName" : "appname")
             + " for row " + index + "\n");
        _stackatoWindow.focus();
        return;
    }
    var this_ = this;
    var terminationCallback = function(retval) {
        log.debug("unbind-service finished => " + retval);
        this_._updateApplicationsTable();
    };
    var unbindServiceFunc = function() {
        this._clearTerminal = true;
        var prompt = null
        this.doApplicationCommand(["unbind-service", serviceName, appName],
                                  terminationCallback,
                                  prompt, "applications_button");
    }.bind(this);
    if (mainRow.fields.health != "STOPPED") {
        var prompt = bundle.formatStringFromName('Stop Application X before unbinding service X',
                                                 [appName, serviceName], 2);
        var response = bundle.GetStringFromName("Yes");
        var text = null;
        var title = bundle.GetStringFromName("Komodo Stackato Sanity Check");
        var response = "Yes";
        var res = ko.dialogs.yesNoCancel(prompt, response, text, title);
        if (res == "Cancel") {
            return;
        } else if (res == "Yes") {
            // stop the service before unbinding
            this.doApplicationCommand(["stop", appName], unbindServiceFunc,
                                      null/*prompt*/, "applications_button");
            return;
        }
    }
    unbindServiceFunc();
};

this.application_showInfo = function(event, infoName) {
    var appName = this._getMainRowAndAppName(event)[1];
    if (!appName) return;
    var this_ = this;
    var terminationCallback = function(retval) {
        log.debug(infoName + " finished => " + retval);
        this_._updateApplicationsTable();
    };
    this._clearTerminal = true;
    this.doApplicationCommand([infoName, appName],
                              terminationCallback,
                              null, "applications_button");
};

this.application_showFiles = function(event, infoName) {
    var row, appName;
    [row, appName] = this._getMainRowAndAppName(event);
    if (!row || !appName) return;
    var numInstances = row.fields.num_instances;
    var results = {};
    var res = ko.windowManager.openOrFocusDialog(
        "chrome://stackatotools/content/stackatoFilesArgs.xul",
        "komodo_stackato",
        "chrome,all,close=yes,resizable,dependent=no,modal=yes",
       {gko:gko, 'window':gWindow, ko:ko,
        stackato: this,
        numInstances:numInstances,
        results:results});
    if (!res) {
        // canceled out
        return;
    }
    var args = ["files", appName];
    if (results.path) {
        args.push(results.path);
    }
    if (results.instanceNum && results.instanceNum != "*") {
        args.push("--instance", results.instanceNum);
    }
    if (results.showAll) {
        args.push("--all");
    }
    this._clearTerminal = true;
    this.doApplicationCommand(args, null, null, null);
};

this.doApplicationCommand = function(args, terminationCallback, prompt, iconID) {
    if (typeof(prompt) == "undefined") prompt = null;
    if (typeof(iconID) == "undefined") iconID = null;
    var obj = {};
    if (prompt) {
        var prompt2 = bundle.formatStringFromName("Please confirm that Stackato should X",
                                                  [prompt], 1);
        var response = "Cancel";
        var text = null;
        var title = bundle.GetStringFromName("Confirm possible destructive action");
        var res = ko.dialogs.okCancel(prompt2, response, text, title);
        if (res != "OK") {
            return;
        }
    }                                      
    this.getStackatoEnv(obj);
    if (!obj.stackato || !obj.path) {
        ko.dialogs.alert(bundle.formatStringFromName("Bailing out of X",
                                                     args, 1));
        return;
    }
    args.push("-n");
    var env = "PATH=" + obj.path;
    var toggleButtonImage, actualCallback;
    var callback2 = {
      callback: function(retval) {
            if (terminationCallback) {
                terminationCallback(retval);
            }
        }
    };
    if (iconID) {
        toggleButtonImage = document.getElementById(iconID);
        toggleButtonImage.classList.add("async_operation");
        actualCallback = {
          callback: function(retval) {
                toggleButtonImage.classList.remove("async_operation");
                callback2.callback(retval);
            }
        }
    } else {
        actualCallback = callback2;
    }
    terminalView.startSession(this._clearTerminal);
    this._clearTerminal = false;
    //terminalView.clear();
    if (!this.stackatoService.runCommandInTerminal(actualCallback,
                                                   g_terminalHandler,
                                                   args.length, args,
                                                   env)) {
        // Instant fail
        actualCallback.callback(-1);
    }
    terminalView.endSession();
};


this._provisionedServicesCurrentRow = function(event) {
    return widgets.views.servicesProvisionedTree.selection.currentIndex;
};

this._updateProvisionedServicesTable = function(outerCallback) {
    if (typeof(outerCallback) == "undefined") outerCallback = null;
    var this_ = this;
    var callback = function() {
        this_.provisionedServiceNames = widgets.views.servicesProvisionedTree.getNames();
        if (outerCallback) {
            outerCallback();
        }
    };
    this.wrapCallbackFunction("getServices",
                              "provisioned_services_button",
                              this.servicesTreeManager,
                              callback);
};

this.provisionedServices_createService = function(event) {
    var results = {};
    var res = ko.windowManager.openOrFocusDialog(
        "chrome://stackatotools/content/stackatoNewService.xul",
        "komodo_stackato",
        "chrome,all,close=yes,resizable,dependent=no,modal=yes",
       {gko:gko, 'window':gWindow, ko:ko,
        stackato: this,
        results:results});
    if (!res) {
        // canceled out
        return;
    }
    if (!results.baseServiceName || !results.provisionedServiceName) {
        return;
    }
    if (this.systemServiceNames.indexOf(results.baseServiceName) === -1) {
        gko.statusBar.AddMessage(bundle.formatStringFromName("Unknown service X",
                                                             [results.baseServiceName], 1),
                                 bundle.GetStringFromName("Stackato"),
                                 3000, true);
        return;
    }
    if (this.provisionedServiceNames.indexOf(results.provisionedServiceName) !== -1) {
        gko.statusBar.AddMessage(bundle.formatStringFromName("Service already defined X",
                                 [results.provisionedServiceName], 1),
                                 bundle.GetStringFromName("Stackato"),
                                 3000, true);
        return;
    }
    var this_ = this;
    var terminationCallback = function(retval) {
        log.debug("create-service finished => " + retval);
        this_._updateProvisionedServicesTable();
    };
    this._clearTerminal = true;
    this.doApplicationCommand(["create-service",
                               results.baseServiceName,
                               results.provisionedServiceName],
                              terminationCallback,
                              null, "provisioned_services_button");
};

this.provisionedServices_deleteService = function(event) {
    var index = this._provisionedServicesCurrentRow(event);
    if (index < 0) return;
    var serviceName = widgets.views.servicesProvisionedTree.getNameAtIndex(index);
    if (!serviceName) {
        log.debug("No serviceName for row " + index);
        return;
    }
    var this_ = this;
    var terminationCallback = function(retval) {
        log.debug("delete-service finished => " + retval);
        this_._updateProvisionedServicesTable();
    };
    var prompt = bundle.formatStringFromName('delete provisioned service X',
                                             [serviceName], 1);
    this._clearTerminal = true;
    this.doApplicationCommand(["delete-service", serviceName],
                              terminationCallback,
                              prompt, "provisioned_services_button");
};

this.getAppForServiceName = function(serviceName) {
    return widgets.views.mainTree.getAppForServiceName(serviceName);
};

this.Credentials = {
    loginManager: Components.classes["@mozilla.org/login-manager;1"]
                            .getService(Components.interfaces.nsILoginManager),
    realm: "stackato.targets",
    
    getTargets: function getTargets() {
        var stackatoRealm = this.realm;
        return this.loginManager.getAllLogins().
               filter(function(loginInfo) loginInfo.httpRealm == stackatoRealm).
               map(function(loginInfo) loginInfo.hostname);
    },
    
    credentialsForHostname: function credentialsForHostname(hostname) {
        var logins = this.loginManager.findLogins({}, hostname, null, this.realm);
        if (logins.length) {
            return [logins[0].username, logins[0].password];
        }
        return [null, null];
    },
    
    addEntry: function addEntry(hostname, username, password) {
        // Delete any old matching entries, and add the new one.
        var newId = Components.classes["@mozilla.org/login-manager/loginInfo;1"]
                           .createInstance(Components.interfaces.nsILoginInfo);
        newId.hostname = hostname;
        newId.httpRealm = this.realm;
        newId.formSubmitURL = null;
        newId.username = username;
        newId.usernameField = "";
        newId.password = password;
        newId.passwordField = "";
        var lm = this.loginManager;
        var logins = lm.findLogins({}, hostname, null, this.realm);
        if (logins.length) {
            //if (logins.length > 1) {
            //    dump("**************** Found "
            //         + logins.length
            //         + " for host hostname "
            //         + hostname
            //         + "\n");
            //}
            logins.slice(1).forEach(function(login) lm.removeLogin(login));
            var oldLogin = logins[0];
            if (oldLogin.username != username
                && oldLogin.password != password) {
                lm.modifyLogin(logins[0], newId);
            } else {
                //dump("No change in login hostname:"
                //     + hostname
                //     + ", user:"
                //     + username
                //     + ", password:"
                //     + password
                //     + "\n");
            }
        } else {
            lm.addLogin(newId);
        }
    },

    removeEntry: function removeEntry(hostname) {
        var lm = this.loginManager;
        var logins = lm.findLogins({}, hostname, null, this.realm);
        for each (var login in logins) {
                try {
                    lm.removeLogin(login);
                } catch(ex) {
                    log.exception(ex, "Problem removing host "
                                  + hostname
                                  + " from login manager");
                }
            }
    },

    __EOD__: null
}

}).apply(ko.stackato);
