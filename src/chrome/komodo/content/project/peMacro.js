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

if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.projects)=='undefined') {
    ko.projects = {};
}

(function() { // ko.projects
var log = ko.logging.getLogger('ko.projects');

 this.addMacro = function peMacro_addMacro(/*koIPart|koITool*/ parent,
                                           /*koIPart|koITool*/ part )
{
    if (typeof(part) == "undefined") {
        part = parent.project.createPartFromType('macro');
    }
    part.setStringAttribute('name', 'New Userscript');
    var obj = new Object();
    obj.item = part;
    obj.parent = parent;
    obj.task = 'new';
    ko.windowManager.openOrFocusDialog(
        "chrome://komodo/content/project/macroProperties.xul",
        "komodo_macroProperties",
        "chrome,centerscreen,close=yes,dependent=no,resizable=yes", obj);
}

this.executeMacro = function macro_executeMacro(part, async, observer_arguments)
{
    log.info("executeMacro part.id:"+part.id);
    if (ko.macros.recorder.mode == 'recording') {
        // See bug 79081 for why we can't have async macros while recording.
        async = false;
    }
    try {
        ko.macros.recordPartInvocation(part);
        var language = part.getStringAttribute('language').toLowerCase();
        if (typeof(async) == "undefined")
            async = part.getBooleanAttribute('async');
        if (async
            && (language == 'javascript'
                || typeof(observer_arguments) != "undefined")) {
            // Python notification observers use this technique.
            setTimeout(_executeMacro, 10,
                       part, false, observer_arguments);
        } else {
            return _executeMacro(part, async, observer_arguments);
        }
    } catch (e) {
        log.exception(e);
    }
    return false;
}


this.executeMacroById = function macro_executeMacroById(id, asynchronous) {
    try {
        var macroPart = ko.toolbox2.findToolById(id);
        var retval = _executeMacro(macroPart,
                                   (asynchronous
                                    && ko.macros.recorder.mode != 'recording'));
        return retval;
    } catch (e) {
        log.exception(e);
    }
    return false;
}

function _executeMacro(part, asynchronous, observer_arguments) {
    // Returns true if there was a problem running the macro
    // The synchronous flag is not used for JavaScript, since the timeout
    // has already occurred by the time we get called here.  JS execution
    // isn't in another thread, just on a timeout.
    if (typeof(observer_arguments) == "undefined") {
        observer_arguments = null;
    }
    try {
        ko.macros.recorder.suspendRecording();
        var language = part.getStringAttribute('language').toLowerCase();
        var retval = false;
        var exception = null;
        var view = null;
        
        if (observer_arguments
            && observer_arguments.subject
            && observer_arguments.subject.nodeName
            && observer_arguments.subject.nodeName == 'view') {
            view = observer_arguments.subject;
        }
        if (!view) {
            try {
                view = ko.views.manager.currentView;
            } catch(ex) {}
        }
        
        var editor = null;
        if (view && view.getAttribute('type') == 'editor' && view.scintilla && view.scintilla.scimoz) {
            editor = view.scintilla.scimoz;
        }
        switch (language) {
            case 'javascript':
                try {
                    retval = ko.macros.evalAsJavaScript(part.value, part,
                                                        observer_arguments, view);
                } catch (e) {
                    exception = String(e);
                }
                break;
            case 'python':
                try {
                    var koDoc = null;
                    if (view && view.koDoc) {
                        koDoc = view.koDoc;
                    }
                    editor = null;
                    if (view && view.getAttribute('type') == 'editor' && view.scimoz) {
                        editor = view.scimoz;
                    }
                    if (!observer_arguments) {
                        retval = part.evalAsPython(document, window, editor,
                                                   koDoc, view,
                                                   part.value, asynchronous);
                    } else {
                        retval = part.evalAsPythonObserver(document, window, editor,
                                                   koDoc, view,
                                                   part.value,
                                                   false,
                                                   observer_arguments['subject'],
                                                   observer_arguments['topic'],
                                                   observer_arguments['data']);
                    }
                } catch (e) {
                    log.exception(e);
                    var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
                                       getService(Components.interfaces.koILastErrorService);
                    exception = lastErrorSvc.getLastErrorMessage();
                }
                break;
            default:
                retval = "Macros written in '"+language+"' aren't supported."
        }
        if (exception) {
            ko.dialogs.alert("There was a problem executing the macro: " +
                         part.getStringAttribute('name'), exception);
            return true;
        } else {
            return retval;
        }
    } catch (e) {
        log.exception(e);
    } finally {
        ko.macros.recorder.resumeRecording();
    }
    return false;
}

this.macroProperties = function macro_editProperties(item)
{
    var obj = {item : item,
               task : 'edit',
               //XXX Would be better to get this from the class, but it isn't exposed.
               imgsrc : 'chrome://komodo/skin/images/macro.png'};
    window.openDialog(
        "chrome://komodo/content/project/macroProperties.xul",
        "Komodo:MacroProperties",
        "chrome,centerscreen,close=yes,dependent=no,resizable=yes", obj);
}

}).apply(ko.projects);

(function() {

    var log = ko.logging.getLogger('ko.macros');


function MacroEventHandler() {
}

var _triggersEnabled = true;

MacroEventHandler.prototype.initialize = function() {

    _triggersEnabled = ko.prefs.getBoolean("triggering_macros_enabled", true);
    ko.prefs.prefObserverService.addObserver(this, "triggering_macros_enabled", false);

    this.log = ko.logging.getLogger('macros.eventHandler');
    //this.log.setLevel(ko.logging.LOG_DEBUG);

    this._trigger_observers = {};

    this._hookedMacrosByTrigger = {
        'trigger_startup' : [],
        'trigger_postopen' : [],
        'trigger_presave' : [],
        'trigger_postsave' : [],
        'trigger_preclose' : [],
        'trigger_postclose' : [],
        'trigger_quit' : [] ,
        'trigger_observer' : []
        };
    var obsSvc = Components.classes["@mozilla.org/observer-service;1"].
                       getService(Components.interfaces.nsIObserverService);
    obsSvc.addObserver(this, 'macro-load', false);
    obsSvc.addObserver(this, 'macro-unload', false);
    obsSvc.addObserver(this, 'javascript_macro',false);
    obsSvc.addObserver(this, 'command-docommand',false);
    obsSvc.addObserver(this, 'toolbox-loaded-local', false);
    obsSvc.addObserver(this, 'toolbox-loaded-global', false);
    obsSvc.addObserver(this, 'toolbox-loaded', false); // synonym for global
    obsSvc.addObserver(this, 'toolbox-unloaded', false);
    obsSvc.addObserver(this, 'toolbox-unloaded-local', false);
    obsSvc.addObserver(this, 'toolbox-unloaded-global', false);

    ko.main.addWillCloseHandler(this.finalize, this);

    this.loadTriggerMacros("" /* all macros */);
}

MacroEventHandler.prototype.finalize = function() {
    try {
        ko.prefs.prefObserverService.removeObserver(this, "triggering_macros_enabled");

        var obsSvc = Components.classes["@mozilla.org/observer-service;1"].
                           getService(Components.interfaces.nsIObserverService);
        obsSvc.removeObserver(this, 'macro-load');
        obsSvc.removeObserver(this, 'macro-unload');
        obsSvc.removeObserver(this, 'javascript_macro');
        obsSvc.removeObserver(this, 'command-docommand');
        obsSvc.removeObserver(this, 'toolbox-loaded-local');
        obsSvc.removeObserver(this, 'toolbox-loaded-global');
        obsSvc.removeObserver(this, 'toolbox-loaded'); // synonym for global
        obsSvc.removeObserver(this, 'toolbox-unloaded');
        obsSvc.removeObserver(this, 'toolbox-unloaded-local');
        obsSvc.removeObserver(this, 'toolbox-unloaded-global');
    } catch(ex) {
        this.log.exception(ex);
    }
}

MacroEventHandler.prototype._triggerWrapper = {
    observe : function(subject, topic, data) {
        // 'this' isn't 'me', so call the global singleton
        if (typeof(ko) == "undefined" || !ko) {
            //this ko has shutdown (or isn't defined yet)
            return false;
        } else if (!_triggersEnabled) {
            return false;
        }
        var observer_arguments = {
            subject: subject,
            topic  : topic,
            data   : data
        }
        var macro_list = ko.macros.eventHandler._hookedMacrosByTrigger['trigger_observer'];
        for (var macro, i = 0; macro = macro_list[i]; i++) {
            if (macro.hasAttribute("trigger_observer_topic")
                && macro.getStringAttribute("trigger_observer_topic") == topic
                && ko.projects.executeMacro(macro, macro.getBooleanAttribute('async'),
                                            observer_arguments)) {
                return true;
            }
        }
        return false;
    }
};
    
MacroEventHandler.prototype.callHookedMacros = function(trigger, viewOrURI) {
    if (!_triggersEnabled) {
        return false;
    }
    var observer_arguments;
    if (typeof(viewOrURI) != 'undefined') {
        observer_arguments = {
            subject: viewOrURI,
            topic  : null,
            data   : null
        };
    } else {
        observer_arguments = null;
    }
    var macro_list = this._hookedMacrosByTrigger[trigger];
    for (var macro, i = 0; macro = macro_list[i]; i++) {
        if (ko.projects.executeMacro(macro, macro.getBooleanAttribute('async'),
                                     observer_arguments)) {
            return true;
        }
    }
    return false;
}

MacroEventHandler.prototype._findMacro = function(macro_list, macropart) {
    for (var i = 0; i < macro_list.length; i++) {
        if (macro_list[i].id == macropart.id) {
            return i;
        }
    }
    return -1;
};

// Sort ascending; sort unranked macros after ranked, 
// and preserve temporal order -- new macros appear after
// equivalently ordered old ones.

MacroEventHandler.prototype._insertNewMacro = function(macro_list, new_macro) {
    if (!new_macro.hasAttribute('rank')) {
        // The newest unranked macro goes on the end.
        macro_list.push(new_macro);
        return;
    }
    var new_rank_val = new_macro.getLongAttribute('rank');
    var pos = macro_list.length; // A.splice(A.len, 0, item) === A.push(item)
    for (var curr_macro, i = 0; curr_macro=macro_list[i]; i++) {
        if (!curr_macro.hasAttribute('rank')) {
            pos = i;
            break;
        }
        if (new_rank_val < curr_macro.getLongAttribute('rank')) {
            pos = i;
            break;
        }
    }
    macro_list.splice(pos, 0, new_macro);
}

MacroEventHandler.prototype.addMacro = function(macropart) {
    // A macro has been added -- we should find out if it
    // has any 'hooks'
    if (macropart.hasAttribute('trigger_enabled') &&
        macropart.getBooleanAttribute('trigger_enabled')) {
        var trigger = macropart.getStringAttribute('trigger');
        var macro_list = this._hookedMacrosByTrigger[trigger];
        var idx = this._findMacro(macro_list, macropart);
        if (idx >= 0) {
            // This routinely happens when a toolbox or project containing
            // trigger macros is reloaded.
            this.log.info("Couldn't add userscript "
                          + macropart.id
                          + " ("
                          + macropart.name
                          + ") to list of hooked userscripts for trigger "
                          + trigger
                          + ": it was already in the list.");
            return;
        }
        this._insertNewMacro(macro_list, macropart);
        if (trigger == 'trigger_observer') {
            this._addObserverMacro(macropart);
        }
    } else {
        this.log.debug("Userscript " + macropart.name + " has no trigger");
    }
}

MacroEventHandler.prototype.loadTriggerMacros = function(dbPath) {
    var macros = ko.toolbox2.getTriggerMacros(dbPath);
    var this_ = this;
    macros.map(function(macro) {
            this_.addMacro(macro);
        });
};

MacroEventHandler.prototype.unloadTriggerMacros = function(dbPath) {
    var macros = ko.toolbox2.getTriggerMacros(dbPath);
    var this_ = this;
    macros.map(function(macro) {
            this_.removeMacro(macro);
        });
};

MacroEventHandler.prototype._addObserverMacro = function(macropart) {
    var topic = macropart.getStringAttribute('trigger_observer_topic');
    if (!(topic in this._trigger_observers)) {
        this._trigger_observers[topic] = 1;
        var obsSvc = Components.classes["@mozilla.org/observer-service;1"].
               getService(Components.interfaces.nsIObserverService);
        obsSvc.addObserver(this._triggerWrapper, topic, false);
    } else {
        this._trigger_observers[topic] += 1;
    }
};

MacroEventHandler.prototype._removeObserverMacro = function(macropart, topic) {
    if (!(topic in this._trigger_observers)) {
        this.log.warn("Unexpected precondition failure: "
                      + "Removing an unused observer ("
                      + topic
                      + "), userscript "
                      + macropart.name
                      + ", project "
                      + macropart.project.url
                      + "\n");
        return;
    }
    this._trigger_observers[topic] -= 1;
    if (this._trigger_observers[topic] <= 0) {
        var obsSvc = Components.classes["@mozilla.org/observer-service;1"].
               getService(Components.interfaces.nsIObserverService);
        obsSvc.removeObserver(this._triggerWrapper, topic);
        delete this._trigger_observers[topic];
    }
};

MacroEventHandler.prototype.updateMacroHooks = function(item, old_props, new_props) {
    var trigger_topic = (old_props.trigger == 'trigger_observer'
                         ? old_props.trigger_observer_topic : null);
    if (!old_props.trigger_enabled) {
        if (new_props.trigger_enabled) {
            this.addMacro(item);
        }
    } else if (!new_props.trigger_enabled) {
        this.removeMacro(item, old_props.trigger, trigger_topic);
    } else if (old_props.trigger != new_props.trigger) {
        this.removeMacro(item, old_props.trigger, trigger_topic);
        this.addMacro(item);
    } else if (new_props.trigger == 'trigger_observer'
               && (old_props.trigger_observer_topic
                   != new_props.trigger_observer_topic)) {
        this.removeMacro(item, old_props.trigger, trigger_topic);
        this.addMacro(item);
    } else if (old_props.rank != new_props.rank) {
        var macro_list = this._hookedMacrosByTrigger[new_props.trigger];
        var idx = this._findMacro(macro_list, item);
        if (idx >= 0) {
            macro_list.splice(idx, 1); // remove it
        } else {
            this.log.info("Expected to find userscript "
                          + item.name
                          + " on the list for "
                          + new_props.trigger
                          + ", but didn't\n.");
        }
        this._insertNewMacro(macro_list, item);
        // No updates needed for notification triggers
    }
};

MacroEventHandler.prototype.removeMacro = function(macropart, trigger, topic) {
    // A macro has been removed -- we should remove it from
    // the list of hooks
    try {
        if (typeof(trigger) == "undefined") {
            // See if we have this macro in a list
            if (macropart.hasAttribute('trigger_enabled') &&
                macropart.getBooleanAttribute('trigger_enabled')) {
                trigger = macropart.getStringAttribute('trigger');
            } else {
                return;
            }
        }
        var macro_list = this._hookedMacrosByTrigger[trigger];
        var idx = this._findMacro(macro_list, macropart);
        if (idx >= 0) {
            macro_list.splice(idx, 1); // remove it
            if (trigger == 'trigger_observer') {
                if (typeof(topic) == "undefined") {
                    topic = ((macropart.getStringAttribute("trigger_observer_topic"))
                             ? macropart.getStringAttribute("trigger_observer_topic") : null);
                }
                if (topic) {
                    this._removeObserverMacro(macropart, topic);
                } else {
                    this.log.warn("Can't find a topic for observer "
                                  + macropart.name
                                  + " in project "
                                  + macropart.project.name);
                }
            }
            return;
        }
    } catch (e) {
        this.log.exception(e);
    }
    this.log.error("Couldn't remove userscript from list of hooked userscripts.");
}

// IMPORTANT: Macros need to wait for the toolbox to load, which may occur after
//            the editor (views) have alreay been loaded. This means we must
//            check if the macro system is ready, and if it's not, store delayed
//            entries in _delayedHooks, which get called later - after the
//            toolboxes have been loaded.

var _didStartup = false;
var _delayedHooks = [];

function _runDelayedHooks() {
    var hook;
    for (var i = 0; i < _delayedHooks.length; ++i) {
        hook = _delayedHooks[i];
        hook[0].call(ko.macros.eventHandler, hook[1]);
    }
    _delayedHooks = [];
}

MacroEventHandler.prototype.hookOnStartup = function() {
    return this.callHookedMacros('trigger_startup');
}

MacroEventHandler.prototype.hookPostFileOpen = function(view) {
    if (!_didStartup) {
        _delayedHooks.push([this.hookPostFileOpen, view]);
        return false;
    }
    return this.callHookedMacros('trigger_postopen', view);
}

MacroEventHandler.prototype.hookPreFileSave = function(view) {
    return this.callHookedMacros('trigger_presave', view);
}

MacroEventHandler.prototype.hookPostFileSave = function(view) {
    return this.callHookedMacros('trigger_postsave', view);
}

MacroEventHandler.prototype.hookPreFileClose = function(view) {
    return this.callHookedMacros('trigger_preclose', view);
}

MacroEventHandler.prototype.hookPostFileClose = function(uri) {
    return this.callHookedMacros('trigger_postclose', uri);
}

MacroEventHandler.prototype.hookOnQuit = function peMacro_hookOnQuit() {
    if (this.callHookedMacros('trigger_quit')) {
        var msg = "Userscript interrupted shutdown procedure.";
        require("notify/notify").send(msg, "tools", {priority: "warning"});
        return false;
    }
    return true;
}

MacroEventHandler.prototype.observe = function(part, topic, code)
{
    try {
        //dump(topic + ": " + part + "\n");
        switch (topic) {
            case 'triggering_macros_enabled':
                // Update preference.
                _triggersEnabled = ko.prefs.getBoolean("triggering_macros_enabled", true);
                break;
            case 'macro-load':
                if (ko.windowManager.getMainWindow() != window) {
                    return;
                }
                this.addMacro(part);
                break;
            case 'macro-unload':
                if (ko.windowManager.getMainWindow() != window) {
                    return;
                }
                this.removeMacro(part);
                break;
            case 'javascript_macro':
                if (ko.windowManager.getMainWindow() != window) {
                    return;
                }
                // dump("part = " + part + "\n");
                ko.macros.evalAsJavaScript(code);
                break;
            case 'command-docommand':
                // Called from a Python macro
                // If the user does a multi-window switch into code
                // that runs komodo.doCommand() outside a macro context,
                // this command might not run as expected.
                if (part == window) {
                    ko.commands.doCommand(code);
                } else {
                    //this.log.debug("command-docommand: not in current window for code: " + code);
                }
                break;
            case 'toolbox-loaded':
            case 'toolbox-loaded-local':
            case 'toolbox-loaded-global':
                if (topic != 'toolbox-loaded-global'
                    && ko.windowManager.getMainWindow() != window) {
                    return;
                }
                this.loadTriggerMacros(code);
                break;
            case 'toolbox-unloaded':
            case 'toolbox-unloaded-local':
            case 'toolbox-unloaded-global':
                if (topic != 'toolbox-unloaded-global'
                    && ko.windowManager.getMainWindow() != window) {
                    return;
                }
                this.unloadTriggerMacros(code);
                break;
        };
    } catch (e) {
        this.log.exception(e);
    }
}
this.eventHandler = new MacroEventHandler();
// safe to use ko.main because this file is loaded only in komodo.xul

// Calling addCanCloseHandler is the same as explicitly observing
// quit-application-requested and then calling ko.macros.eventHandler.hookOnQuit()
// This way is simpler because we don't have to QI the observe function's first arg
// for nsIBoolean, and handle the double-negative (set the .data field to true if we
// want to quit, but hookOnQuit() returns false if we're to quit).
ko.main.addCanCloseHandler(function () { return ko.macros.eventHandler.hookOnQuit() });


/**
 * The main toolboxes are loaded, go and initialize the macro triggers.
 */
this.onToolboxInitialized = function() {
    // Macro parts are now available.
    this.eventHandler.initialize();
    this.eventHandler.hookOnStartup();
    // Run any delayed file-open hooks.
    _didStartup = true;
    _runDelayedHooks();
}


function _macro_error(ex, badLine, part) {
    const errorType = ex.name == "SyntaxError" ? "Syntax" : "Runtime";
    const bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
          .getService(Components.interfaces.nsIStringBundleService)
          .createBundle("chrome://komodo/locale/project/macro.properties");
    const errorTypeText = bundle.GetStringFromName(errorType);
    const title = bundle.formatStringFromName("Macro X Error",
                                              [errorTypeText],
                                              1);
    const prompt = (part
                    ? bundle.formatStringFromName("X error in macro Y",
                                                  [errorTypeText, part.name], 2)
                    : bundle.formatStringFromName("X error in macro",
                                                  [errorTypeText], 1));
    var msg = badLine ? badLine.replace(/[\r\n]+$/, "") + "\n\n" : "";
    if (ex.name == "SyntaxError") {
        msg += ko.logging.strObject(ex, "exception") + "\n\n";
    } else {
        msg += (ex.name + ": " +
                ex.message + "\n\n" +
                ko.logging.strObject(ex, "exception"));
    }
    ko.dialogs.alert(prompt, msg, title, null, "chrome,modal,titlebar,resizable");
}

this.__defineGetter__("current",
function()
{
    var _partSvc = Components.classes["@activestate.com/koToolbox2Service;1"]
        .getService(Components.interfaces.koIToolbox2Service);
    return _partSvc.runningMacro;
});

this.__defineSetter__("current",
function(macro)
{
    var _partSvc = Components.classes["@activestate.com/koToolbox2Service;1"]
        .getService(Components.interfaces.koIToolbox2Service);
    _partSvc.runningMacro = macro;
});

this.evalAsJavaScript = function macro_evalAsJavascript(__code,
                                                        part, /* = null */
                                                        __observer_arguments, /* = null */
                                                        view /* = currentView */
                                                        ) {
    try {
        if (typeof(part) == 'undefined') {
            part = null;
        }
        if (typeof(__observer_arguments) == 'undefined') {
            __observer_arguments = null;
        }
        if (typeof(view) == 'undefined' || view == null) {
            try {
                view = ko.views.manager.currentView;
            } catch(ex) {}
        }

        ko.macros.current = part;
        var komodo = new _KomodoJSMacroAPI(part, view);
        var __macro_internals = {
            // Hide these locals from the macro's namespace.
            retcode: -1,
            header: (__observer_arguments ? "subject, topic, data" : ""),
            error_type: null, // 'runtime' or 'compiler'
            __eod__: null
        };
        if (!('__base_line_no' in this)) {
            this.__base_line_no = (new Error("get line # hack")).lineNumber + 1;
        }
        try {
            // Keep these calls on the same line so the offsets are consistent
            // when reporting error messages.
            __macro_internals.compiled_func =
                (__observer_arguments
                 ? new Function('komodo', 'subject', 'topic', 'data', __code) : new Function('komodo', __code));
            // eval("(function(" + __macro_internals.header + ") { \n" + __code + "\n })");
            try {
                __macro_internals.retcode =
                    (__macro_internals.header
                     ? __macro_internals.compiled_func(komodo, __observer_arguments.subject, __observer_arguments.topic, __observer_arguments.data) : __macro_internals.compiled_func(komodo));
            } catch(rex) {
                __macro_internals.error_type = 'running';
                __macro_internals.ex = rex;
                __macro_internals.offset = 5;
            }
        } catch (cex) {
            __macro_internals.error_type = 'compiling';
            __macro_internals.ex = cex;
            __macro_internals.offset = 5;
        }
        if (__macro_internals.error_type) {
            let actualLineNumber;
            let ex = __macro_internals.ex;
            let bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
                .getService(Components.interfaces.nsIStringBundleService)
                .createBundle("chrome://komodo/locale/project/macro.properties");
            if (!part) {
                ex.fileName = bundle.GetStringFromName("The current userscript");
            } else {
                try {
                    if (part.url) {
                        var m = /^macro\d*:\/\/.*\/(.*)$/.exec(part.url);
                        if (m) {
                            ex.fileName = m[1];
                        }
                    }
                } catch(ex2) { // Ignore this exception
                }
            }
            actualLineNumber = ex.lineNumber - this.__base_line_no - __macro_internals.offset;
            var codeLines = __code.split(/\r?\n/);
            var msg = null;
            if (actualLineNumber >= 1 &&
                actualLineNumber <= codeLines.length) {
                ex.lineNumber = actualLineNumber;
            }
            _macro_error(ex, codeLines[actualLineNumber - 1], part);
        }
        komodo.destructor();
        komodo = null;
        ko.macros.current = null;
        return __macro_internals.retcode;
    } catch (e) {
        log.exception(e);
    }
    return false;
}

this.recordPartInvocation = function macro_recordPartInvocation(part) {
    try {
        // We'll do the macro work ourselves using the name of the part
        // instead of the encoded contents of the run command -- the
        // resulting macro has a _reference_ to the run command, which
        // seems more representative of what the user expects (and means
        // that the run command can be developed independently of the
        // macro.
        var mainWindow = ko.windowManager.getMainWindow();
        if (!mainWindow) {
            return;
        }
        var wko = mainWindow.ko;
        if (typeof(wko.macros.recorder) != 'undefined' &&
            wko.macros.recorder &&
            wko.macros.recorder.mode == 'recording') {
            var name = part.getStringAttribute('name');
            var type = part.type;
            var runtxt = "_part = komodo.findPart('"+type+"', '" + name + "'" + ")\n";
            runtxt += "if (!_part) {alert(\"Couldn't find a " + type + " called '" + name + "' when executing macro.\"); return\n}\n";
            runtxt += "ko.projects.invokePart(_part);\n";
            wko.macros.recorder.appendCode(runtxt);
        }
    } catch (e) {
        log.exception(e);
    }
}


/**
 * Komodo JS Macro Object, DEPRECATED
 *
 * The original Komodo JS Macro object is deprecated, use the following
 * to map to the current correct usage
 * 
 * komodo.doc -> ko.views.manager.currentView.koDoc (DROPPED in Komodo 7.0.0a2, use `koDoc`)
 * komodo.document -> ko.views.manager.currentView.koDoc (DROPPED in Komodo 7.0.0a2, use `koDoc`)
 * komodo.koDoc -> ko.views.manager.currentView.koDoc
 * komodo.editor -> ko.views.manager.currentView.scimoz
 * komodo.view -> ko.views.manager.currentView
 * komodo.macro -> macro (ie. the running macro, koIPart_macro interface, available in 4.2)
 * komodo.openURI -> ko.open.URI
 * komodo.window -> window
 * komodo.domdocument -> document
 * komodo.components -> Components
 * komodo.doCommand -> ko.commands.doCommand
 * komodo.getWordUnderCursor -> ko.interpolate.getWordUnderCursor(ko.views.manager.currentView.scimoz)
 * komodo.interpolate -> ko.interpolate.interpolateString
 * 
 * 
 * komodo.interpolate is more correctly emulated by doing:
 * 
 * var queryTitle = "Macro '"+macro.getStringAttribute("name")+"' Query";
 * result = ko.interpolate.interpolateString(s, bracketed, queryTitle);
 */
function _KomodoJSMacroAPI(macro, view)
{
    log.debug("_KomodoJSMacroAPI()");
    try {
        this.koDoc = null;
        if (view && view.koDoc) {
            this.koDoc = view.koDoc;
        }
        this.editor = null;
        if (view && view.scimoz) {
            this.editor = view.scimoz;
        }
        this.view = view;
        this.macro = macro;
        // Point this function to the global JS function
        this.openURI = ko.open.URI;

        this.window = window;
        this.domdocument = document;
        this.components = Components;
    } catch(ex) {
        log.exception(ex);
    }
}
_KomodoJSMacroAPI.prototype.constructor = _KomodoJSMacroAPI;

_KomodoJSMacroAPI.prototype.destructor = function() {
    delete this.editor;
    delete this.view;
    delete this.window;
    delete this.koDoc;
    delete this.domdocument;
}

_KomodoJSMacroAPI.prototype.assertMacroVersion = function(version) {
    if (version < ko.macros.CURRENT_MACRO_VERSION) {
        alert("This macro was generated with an older version of Komodo, "
              + "and might no longer work correctly.  \n"
              + "This message can be suppressed by editing the userscript "
              + "and changing the 'assertMacroVersion' value to "
              + ko.macros.CURRENT_MACRO_VERSION);
    }
};
_KomodoJSMacroAPI.prototype.doCommand = ko.commands.doCommand;
_KomodoJSMacroAPI.prototype.findPart = function(toolType, toolName) {
    var res = ko.toolbox2.getToolsByTypeAndName(toolType, toolName);
    if (!res.length) return null;
    return res[0];
}
_KomodoJSMacroAPI.prototype.getWordUnderCursor = function()
{
    return ko.interpolate.getWordUnderCursor(this.editor);
}

_KomodoJSMacroAPI.prototype.interpolate = function(s, bracketed /*=false*/)
{
    var queryTitle = null;
    if (this.macro) {
        queryTitle = "Macro '"+this.macro.getStringAttribute("name")+"' Query";
    }
    return ko.interpolate.interpolateString(s, bracketed, queryTitle);
}

}).apply(ko.macros);
