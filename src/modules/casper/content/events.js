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
include('chrome://jslib/content/io/chromeFile.js');

if (typeof(Casper) == 'undefined') {
    var Casper = {};
}
if (typeof(Casper.Events) == 'undefined') {
    Casper.Events = {};
}


Casper.Events.log = Casper.Logging.getLogger('Casper::Events');
Casper.Events.util = {
    cprops: ["type", "eventPhase", "bubbles", "cancelable", "detail", "button",
            "isChar", "charCode", "shiftKey", "ctrlKey", "altKey", "keyCode",
            "metaKey"],
    props: ["type", "eventPhase", "bubbles", "cancelable", "detail", "button",
            "isChar", "charCode", "shiftKey", "ctrlKey", "altKey", "keyCode",
            "metaKey", "clientX", "clientY", "layerX", "layerY", "screenX", "screenY",
            "timeStamp"],
    matchEvent: function(e1, e2) {
        if (e1.originalTargetXPath != e2.originalTargetXPath)
            return false;
        for (var p in Casper.Events.util.cprops) {
            var prop = Casper.Events.util.cprops[p];
            if (prop in e1) {
                if (!(prop in e2))
                    return false;
                if (e1[prop] != e2[prop])
                    return false;
            }
        }
        return true;
    },
    serialize: function(event) {
        try {
        var generator = new Casper.XPath.XPathGenerator();
        generator.includeAttributeNS(null, "id", true);
        generator.includeAttributeNS(null, "anonid", true);
        var cloned = {};
        // we dont want to serialize everything, just stuff we must have to
        // recreate events
        for (var p in Casper.Events.util.props) {
            if (Casper.Events.util.props[p] in event)
                cloned[Casper.Events.util.props[p]] = event[Casper.Events.util.props[p]];
        }
        cloned["target"] = null;
        cloned["targetXPath"] = null;
        if (event.target) {
            cloned["targetXPath"] = generator.generateXPath(event.target, event.target.ownerDocument );
        }
        cloned["currentTarget"] = null;
        cloned["currentTargetXPath"] = null;
        if (event.currentTarget) {
            cloned["currentTargetXPath"] = generator.generateXPath(event.currentTarget, event.currentTarget.ownerDocument );
        }
        cloned["originalTarget"] = null;
        cloned["originalTargetXPath"] = null;
        if (event.originalTarget) {
            cloned["originalTargetXPath"] = generator.generateXPath(event.originalTarget, event.originalTarget.ownerDocument );
        }
        cloned["enabled"]=true;
        cloned["action"]="fire";
        cloned["waitTimeout"]=3000;
        } catch(e) { Casper.Events.log.exception(e); }
        return cloned;
    },
    
    _deserializeNodeXPath: function(path, doc) {
        // XXX better way to choose document?
        try {
            return Casper.XPath.evaluatePaths(doc, path)[0];
        } catch (e) {
            Casper.Events.log.exception(e);
        }
        return null;
    },
    
    deserialize: function(evt, doc) {
        if (typeof(doc) == 'undefined') {
            doc = document;
        }
        if (evt.targetXPath)
            evt.target = Casper.Events.util._deserializeNodeXPath(evt.targetXPath, doc);
        if (evt.currentTargetXPath)
            evt.currentTarget = Casper.Events.util._deserializeNodeXPath(evt.currentTargetXPath, doc);
        if (evt.originalTargetXPath)
            evt.originalTarget = Casper.Events.util._deserializeNodeXPath(evt.originalTargetXPath, doc);
        return evt;
    }


}

Casper.Events.factory = {
    _handlers: {},
    create: function(name) {
        if (typeof(Casper.Events.handler[name]) == 'function') {
            return new Casper.Events.handler[name]();
        }
        return new Casper.Events.base.simple(name);
    }, 
    get: function(name) {
        if (typeof(name) == 'undefined') {
            var l = [];
            for (name in Casper.Events.factory._handlers) {
                l[l.length] = Casper.Events.factory._handlers[name];
            }
            return l;
        }
        if (!(name in Casper.Events.factory._handlers)) {
            Casper.Events.factory._handlers[name] = Casper.Events.factory.create(name);
        }
        return Casper.Events.factory._handlers[name];
    }
}

Casper.Events.dispatch = {
    /* these are the actual dispatching functions, they create a DOM
       event and dispatch it into the document.
    */
    simpleEvent: function(target, evt)
    {
        if (!target)
          return;
        var event = target.ownerDocument.createEvent('Events'); // same as HTMLEvents
        event.initEvent(evt.type, evt.bubbles, evt.cancelable);
        target.dispatchEvent(event);
    },
        
    UIEvent: function(target, evt)
    {
        if (!target)
          return;
        var event = target.ownerDocument.createEvent("UIEvents");
        event.initUIEvent(evt.type, evt.bubbles, evt.cancelable, target.ownerDocument.defaultView, evt.detail);
        target.dispatchEvent(event);
    },
    
    keyEvent: function(target, evt)
    {
        // not yet tested
        if (!target)
          return;
        var event = target.ownerDocument.createEvent("KeyEvents");
        event.initKeyEvent(evt.type, evt.bubbles, evt.cancelable,
                           target.ownerDocument.defaultView, evt.ctrlKey, evt.altKey, evt.shiftKey,
                           evt.metaKey, evt.keyCode, evt.charCode);
        target.dispatchEvent(event);
    },
    
    mouseEvent: function(target, evt)
    {
        if (!target)
          return;
        var ev = target.ownerDocument.createEvent("MouseEvents");
        
        var windowbox = target.ownerDocument.getBoxObjectFor(target.ownerDocument.documentElement);
        var box = target.ownerDocument.getBoxObjectFor(target);
        var screenXArg = windowbox.screenX+evt.clientX;
        var screenYArg = windowbox.screenY+evt.clientY;
        var clientXArg = box.x + evt.layerX - 1;
        var clientYArg = box.y + evt.layerY - 1;
        //dump("mouseEvent:\n");
        //dump("   type "+evt.type+"\n");
        //dump("   target "+target.nodeName+"\n");
        //dump("   window screenX "+target.ownerDocument.defaultView.screenX+" screenY "+target.ownerDocument.defaultView.screenY+"\n");
        //dump("   docEl screenX "+windowbox.screenX+" screenY "+windowbox.screenY+"\n");
        //dump("   target x "+box.x+" y "+box.y+"\n");
        //dump("   layer x "+evt.layerX+" y "+evt.layerY+"\n");
        //dump(" - screenXArg "+screenXArg+"\n");
        //dump(" - screenYArg "+screenYArg+"\n");
        //dump(" - clientXArg "+clientXArg+"\n");
        //dump(" - clientYArg "+clientYArg+"\n");
        ev.initMouseEvent(evt.type, //in DOMString typeArg,
                    evt.bubbles, //in boolean canBubbleArg,
                    evt.cancelable, //in boolean cancelableArg,
                    target.ownerDocument.defaultView, //in nsIDOMAbstractView viewArg,
                    evt.detail, //in long detailArg,
    
                    screenXArg, //in long screenXArg,
                    screenYArg, //in long screenYArg,
                    // XXX is it correct to use layerX here?
                    clientXArg, //in long clientXArg,
                    clientYArg, //in long clientYArg,
    
                    evt.ctrlKey, //in boolean ctrlKeyArg,
                    evt.altKey, //in boolean altKeyArg,
                    evt.shiftKey, //in boolean shiftKeyArg,
                    evt.metaKey, //in boolean metaKeyArg,
                    evt.button, //in unsigned short buttonArg,
                    null //in nsIDOMEventTarget relatedTargetArg
                    );
        //dump("   ev layer x "+ev.layerX+" y "+ev.layerY+"\n");
        //dump("   ev clientX "+ev.clientX+" clientY "+ev.clientY+"\n");
        target.dispatchEvent(ev);
    }
}

Casper.Events.base = {
    /* these are base implementations of handler classes that are
       subclassed in Casper.Events.handlers
    */
    simple: function(name) {
        this.eventName=name;
        this._hooks = [];
        
        this.listen = function(aWindow, aListener) {
            var obj = {
                docWindow: aWindow,
                handler: function(event) { aListener.handleEvent(event); }
            }
            this._hooks.push(obj);
            aWindow.addEventListener(this.eventName, obj.handler, true);
        }
        
        this.stop = function(aWindow, listener) {
            for (var i in this._hooks) {
                var obj = this._hooks[i]
                if (obj.docWindow == aWindow) {
                    aWindow.removeEventListener(this.eventName, obj.handler, true);
                    obj.handler = null;
                    obj.docWindow = null;
                    this._hooks.splice(i, 1);
                    break;
                }
            }
        }
        
        this.doEvent = function(e, targetWindow) {
            var evt = Casper.Events.util.deserialize(e, targetWindow.document);
            return Casper.Events.dispatch.simpleEvent(evt.originalTarget, evt);
        }
    },

    keyevent: function(name) {
        this.prototype = new Casper.Events.base.simple();
        Casper.Events.base.simple.apply(this, [name]);
        this.doEvent = function(e, targetWindow) {
            var evt = Casper.Events.util.deserialize(e, targetWindow.document);
            return Casper.Events.dispatch.keyEvent(evt.originalTarget, evt);
        }
    },

    mouseevent: function(name) {
        this.prototype = new Casper.Events.base.simple();
        Casper.Events.base.simple.apply(this, [name]);
        this.doEvent = function(e, targetWindow) {
            var evt = Casper.Events.util.deserialize(e, targetWindow.document);
            return Casper.Events.dispatch.mouseEvent(evt.originalTarget, evt);
        }
    },
    
    uievent: function(name) {
        this.prototype = new Casper.Events.base.simple();
        Casper.Events.base.simple.apply(this, [name]);
        this.doEvent = function(e, targetWindow) {
            var evt = Casper.Events.util.deserialize(e, targetWindow.document);
            return Casper.Events.dispatch.UIEvent(evt.originalTarget, evt);
        }
    }
}

Casper.Events.handler = {
    /* these are the actual event handler classes.  The names of the
       classes should match the DOM event name
    */
    mousedown: function() {
        this.prototype = new Casper.Events.base.mouseevent();
        Casper.Events.base.mouseevent.apply(this, ['mousedown']);
    },

    mouseup: function() {
        this.prototype = new Casper.Events.base.mouseevent();
        Casper.Events.base.mouseevent.apply(this, ['mouseup']);
    },

    input: function() {
        this.prototype = new Casper.Events.base.uievent();
        Casper.Events.base.uievent.apply(this, ['input']);
    },

    text: function() {
        this.prototype = new Casper.Events.base.keyevent();
        Casper.Events.base.uievent.apply(this, ['text']);
    },

    keyup: function() {
        this.prototype = new Casper.Events.base.keyevent();
        Casper.Events.base.keyevent.apply(this, ['keyup']);
    },

    keydown: function() {
        this.prototype = new Casper.Events.base.keyevent();
        Casper.Events.base.keyevent.apply(this, ['keydown']);
    },

    keypress: function() {
        this.prototype = new Casper.Events.base.keyevent();
        Casper.Events.base.keyevent.apply(this, ['keypress']);
    },
    
    // more simple event emulation
    
    click: function() {
        this.prototype = new Casper.Events.base.mouseevent();
        Casper.Events.base.mouseevent.apply(this, ['click']);
    },

    blur: function() {
        this.prototype = new Casper.Events.base.simple();
        Casper.Events.base.simple.apply(this, ['blur']);
        this.doEvent = function(e, targetWindow) {
            var evt = Casper.Events.util.deserialize(e, targetWindow.document);
            return evt.target.blur();
        }
    },
    
    focus: function() {
        this.prototype = new Casper.Events.base.simple();
        Casper.Events.base.simple.apply(this, ['focus']);
        this.doEvent = function(e, targetWindow) {
            var evt = Casper.Events.util.deserialize(e, targetWindow.document);
            return evt.target.focus();
        }
    },
    
    command: function() {
        this.prototype = new Casper.Events.base.simple();
        Casper.Events.base.simple.apply(this, ['command']);
        this.doEvent = function(e, targetWindow) {
            var evt = Casper.Events.util.deserialize(e, targetWindow.document);
            return evt.target.doCommand();
        }
    },

    load: function() {
        this.prototype = new Casper.Events.base.simple();
        Casper.Events.base.simple.apply(this, ['load']);
        this.doEvent = function(e, targetWindow) {}
    },
    
    unload: function() {
        this.prototype = new Casper.Events.base.simple();
        Casper.Events.base.simple.apply(this, ['unload']);
        this.doEvent = function(e, targetWindow) {}
    }
}

/**
 * nsEventStateManager emulation
 * unfortunately, when we emulate events, the postHandleEvent method
 * of nsEventStateManager is not called.  So, for example, dispatching
 * a tab keypress does not advance focus.  our statemanager will attempt
 * to emulate some of these things so that we get expected results.
 * while not everything will be implemented in the handler, some notes
 * have been made about what I think they need to do.
 */
Casper.Events.StateManager = function() {
    this.log = Casper.Logging.getLogger('Casper::Events::StateManager');
    //this.log.setLevel(Casper.Logging.DEBUG);
    var self = this;
    this.handler = function(event) {
        self.PostHandleEvent(event);
    }
    this.windows = [];
}
Casper.Events.StateManager.constructor = Casper.Events.StateManager;
Casper.Events.StateManager.prototype = {
    start: function(aWindow)
    {
        // install an event bubble listener for events we care about
        this.log.debug("start window listeners");
        this.windows.push(aWindow);
        aWindow.addEventListener("keypress", this.handler, false);
    },
    stop: function(aWindow)
    {
        this.log.debug("stop window listeners");
        this.windows.splice(this.windows.indexOf(aWindow), 1);
        aWindow.removeEventListener("keypress", this.handler, false);
    },
    
    PostHandleEvent: function(event) {
        this.log.debug("PostHandleEvent "+event.type);
        switch(event.type) {
        case "mousedown":
            // seems the most important thing is setting focus
            break;
        case "mouseup":
            // CheckForAndDispatchClick
            break;
        case "DOMScrollMouse":
            // seems like statemanager is where actuall text scroll happens
            break;
        case "dragdrop":
        case "dragexit":
            // GenerateDragDropEnterExit
            break;
        case "keypress":
            try {
            if (event.getPreventDefault()) return;
            if (event.altKey) return;
            switch (event.keyCode) {
            case event.DOM_VK_TAB:
                // if not a control, shift widget focus
                // else shift doc focus
                // XXX how do I know it is a control or not?
                //     if (!((nsInputEvent*)aEvent)->isControl)
                
                //var aWindow = event.target.ownerDocument.defaultView;
                if (event.shiftKey)
                    //aWindow.setTimeout("document.commandDispatcher.rewindFocus();",0);
                    event.target.ownerDocument.commandDispatcher.rewindFocus();
                else
                    //aWindow.setTimeout("document.commandDispatcher.advanceFocus();",0);
                    event.target.ownerDocument.commandDispatcher.advanceFocus();
                break;
            case event.DOM_VK_F6:
                // shift doc focus.  this seems to switch focus from xul to
                // html documents contained within
                // can probably just change focus between visible window.frames
                // var aWindow = event.target.ownerDocument.defaultView;
                // var frames = aWindow.frames
                // get index of current frame, increment or decrement
                // if new index is out of range, focus the primary xul window
                break;
            case event.DOM_VK_PAGE_DOWN:
            case event.DOM_VK_PAGE_UP:
                // page scrolls views if they are scrollable
                break;
            case event.DOM_VK_HOME:
            case event.DOM_VK_END:
                // scrolls views to top/bottom if they are scrollable
                break;
            case event.DOM_VK_UP:
            case event.DOM_VK_DOWN:
                // line scrolls views if they are scrollable
                break;
            case event.DOM_VK_LEFT:
            case event.DOM_VK_RIGHT:
                // horizontal scrolls views if they are scrollable
                break;
            //case 0:
            //    // check for spacebar,
            //    if (event.charCode == 0x20) {
            //        // scroll down a page
            //    }
            //    break;
            default:
                this.log.debug("PostHandleEvent no handler for "+event.keyCode);
            
            }
            } catch(e) {
                this.log.exception(e);
            }
            break;
        case "mouseenter":
            // sets hoverstate
            break;
        case "appcommand": // NS_APPCOMMAND
            // handles back/forward/refresh/stop in browser
            break;
        }
    }
}

Casper.Events.test = function(targetWindow) {
    this.log = Casper.Logging.getLogger('Casper::Events::Test');
    //this.log.setLevel(Casper.Logging.DEBUG);
    this.eventList = [];
    this.complete = null;
    if (typeof(targetWindow) == 'undefined') {
        this.targetWindow = window;
    } else {
        this.targetWindow = targetWindow;
    }
}
Casper.Events.test.constructor = Casper.Events.test;
Casper.Events.test.prototype = {
    listener: null,
    pastEvents: null,
    waitevent: null,
    timeout: null,
    nextEventIndex: 0,
    lastEventIndex: 0,
    get WMSvc() {
        return Components.classes["@mozilla.org/appshell/window-mediator;1"]
                        .getService(Components.interfaces.nsIWindowMediator);
    },
    get topWindow() {
        var top = this.WMSvc.getMostRecentWindow(null);
        if (top != this.targetWindow) {
            this.log.debug("topWindow != targetWindow");
        }
        return top;
    },
    
    replay: function()
    {
        this.nextEventIndex = 0;
        this.lastEventIndex = 0;
        // get all the wait events and add listeners for them
        this.pastEvents = [];
        this.listener = new Casper.Events.EventListener(this, new Casper.Events.StateManager());
        for (var i =0; i < this.eventList.length; i++) {
            if (this.eventList[i].action == 'wait') {
                this.listener.addListener(this.eventList[i].type);
            }
        }
        this.listener.start(this.targetWindow);
        this.targetWindow.focus();
        this.callNextEvent();
    },
    
    doNextEvent: function()
    {
        if (this.nextEventIndex >= this.eventList.length) {
            this.finishRun(null);
            return;
        }
        var e = this.eventList[this.nextEventIndex];
        this.log.debug("doNextEvent..."+this.nextEventIndex+" "+e.type+" enabled? "+e.enabled);
        if (!e.enabled) {
            this.callNextEvent();
            this.nextEventIndex++;
            return;
        }
        var delay = this.nextEventIndex > 0 &&
                        e.timeStamp > 0 && this.eventList[this.lastEventIndex].timeStamp > 0 ?
                            e.timeStamp - this.eventList[this.lastEventIndex].timeStamp: 1;
        //this.log.debug("    delay "+delay);
        this.lastEventIndex = this.nextEventIndex;
        try {
            if (e.action == "fire") {
                this.dispatchEvent(e);
                this.callNextEvent();
            } else
            if (e.action == "wait") {
                this.waitForEvent(e);
            }
        } catch(ex) {
            this.log.exception(ex);
            this.finishRun(ex);
        }
        this.nextEventIndex++;
        this.log.debug("...doNextEvent");
    },
    
    callNextEvent: function()
    {
        // fire the next event
        this.topWindow.setTimeout(function (me) {
                me.doNextEvent();
            }, 0, this);
    },
    
    dispatchEvent: function(e)
    {
        this.log.debug("runEvent "+e.type+" phase "+e.eventPhase+" xpath "+e.originalTargetXPath);
        // events always happen in topmost window
        Casper.Events.factory.get(e.type).doEvent(e, this.topWindow);
    },
    
    finishRun: function(ex)
    {
        this.log.debug("finishRun..."+ex);
        this.listener.stop();
        if (this.complete)
            this.complete(ex);
        else
            throw ex;
    },
    
    _saveDialog: function(basename)
    {
        var nsIFilePicker = Components.interfaces.nsIFilePicker;
        var fp = Components.classes["@mozilla.org/filepicker;1"]
                .createInstance(nsIFilePicker);
        fp.init(window, "Save the file as", nsIFilePicker.modeSave);
        fp.appendFilter("JavaScript Files","*.js;");
        fp.appendFilter("JSON Files","*.json;");
        fp.appendFilter("All Files","*.*; *;");
        fp.defaultString = basename;
        // fp.displayDirectory ?
        
        var res = fp.show();
        if (res != nsIFilePicker.returnCancel) {
          return fp.file.path;
        }
        return null;
    },

    _openDialog: function()
    {
        var nsIFilePicker = Components.interfaces.nsIFilePicker;
        var fp = Components.classes["@mozilla.org/filepicker;1"]
                .createInstance(nsIFilePicker);
        fp.init(window, "Open a JSON file", nsIFilePicker.modeOpen);
        fp.appendFilter("JSON Files","*.json;");
        fp.appendFilter("All Files","*.*; *;");
        // fp.displayDirectory ?
        
        var res = fp.show();
        if (res != nsIFilePicker.returnCancel) {
          return fp.file.path;
        }
        return null;
    },

    getJSON: function(all)
    {
        var elist = [];
        for (var i = 0; i < this.eventList.length; i++) {
            if (all || this.eventList[i].enabled)
                elist.push(this.eventList[i]);
        }
        return Casper.JSON.stringify(elist);
    },
    
    save: function(all)
    {
        try {
        var fname = "test.json";
        var url = this._saveDialog(fname);
        if (!url) return;

        var data = this.getJSON(all);

        // save the file
        var f = new File(url);
        f.open('w');
        f.write(data);
        f.close();
        } catch(e) { this.log.exception(e); }
    },
    
    load: function()
    {
        try {
        var fname = "test.json";
        var url = this._openDialog(fname);
        if (!url) return;

        // read the file
        var f = new File(url);
        f.open('r');
        var data = f.read();
        f.close();

        this.eventList = Casper.JSON.parse(data);
        } catch(e) { this.log.exception(e); }
    },
    
    generate: function(templateFile)
    {
        try {
        if (typeof(templateFile) == 'undefined')
            templateFile = "chrome://casper/content/test/_event_test_template.js";
        // generate js unittest class
        
        // first, load _event_test_template.js
        var cf = new ChromeFile(templateFile);
        cf.open();
        var template = cf.read();
        cf.close();
        
        // get the stringified event data
        var data = this.getJSON(false);

        // ask the user for a test name
        var promptService = Components.classes["@mozilla.org/embedcomp/prompt-service;1"]
                    .getService(Components.interfaces.nsIPromptService);
        var value = new Object();
        if (!promptService.prompt(window, "Test Class Name", "Enter a name for the test case", value, null, new Object())) {
            return;
        }
        var testName = value.value;
        
        // do interpolations
        template = template.replace(/\%EVENT_TEST_CLASSNAME\%/g, testName);
        template = template.replace(/\%EVENT_LIST\%/, data);
        var newline = '\n';
        if (navigator.platform == "Win32") {
            newline = "\r\n";
        }
        template = template.replace(/\r\n|\n|\r/, newline);
        // get a save location
        var fname = "test_"+testName+".js";
        var url = this._saveDialog(fname);
        if (!url) return;

        // save the file
        var f = new File(url);
        f.open('w');
        f.write(template);
        f.close();
        } catch(e) { this.log.exception(e); }
    },
    
    addEvent: function(event)
    {
        this.log.debug("addEvent "+event.type);
        this.eventList[this.eventList.length] = Casper.Events.util.serialize(event);
    },
    
    waitTimeout: function(nextEventIndex)
    {
        if (this.eventHasHappened(event)) return;
        // we did not receive an event and have timed out, we should now assert
        if (this.waitevent) {
            this.log.debug("got a waittimeout, ending event test");
            var e = new Error("event wait timed out");
            this.listener.stop();
            if (this.complete)
                this.complete(e);
            else
                throw e;
        }
    },
    
    eventHasHappened: function(event)
    {
        for (var i = 0; i < this.pastEvents.length; i++) {
            if (Casper.Events.util.matchEvent(this.pastEvents[i], event)) {
                this.log.debug("eventHasHappened!");
                this.pastEvents.splice(i, i+1);
                this.callNextEvent();
                return true;
            }
        }
        return false;
    },
    
    waitForEvent: function(event)
    {
        if (this.eventHasHappened(event)) return;
        // if we got here, the event has not ocured
        this.log.debug("waitForEvent? set a timeout and wait");
        this.waitevent = event;
        this.timeout = this.topWindow.setTimeout(function (me) {
                me.waitTimeout();
            }, event.waitTimeout, this);
    },
    
    handleEvent: function(event)
    {
        var eser = Casper.Events.util.serialize(event);
        // if we have a wait event, match it, otherwise ignore
        this.log.debug("handleEvent "+event.type+" phase "+event.eventPhase);
        if (this.waitevent && Casper.Events.util.matchEvent(eser, this.waitevent)) {
            this.log.debug("    matched an event we're waiting for!");
            this.topWindow.clearTimeout(this.timeout);
            this.waitevent = null;
            this.callNextEvent();
        } else {
            // we have to store these events in case they happen before we
            // get to install the wait.  This can happen if you do a click
            // event then wait for a focus event after it
            this.log.debug("    save it for later");
            this.pastEvents.push(eser);
        }
    }
    
}

Casper.Events.EventListener = function(handlerObj, stateManager) {
    this.log = Casper.Logging.getLogger('Casper::Events::EventListener');
    //this.log.setLevel(Casper.Logging.DEBUG);
    this.handler = handlerObj;
    this.eventType = {};
    this.windows = [];
    var data = Casper.JSON.stringify(this.eventType);
    this.log.debug("events are currently "+data);
    this.stateManager = stateManager;
}
Casper.Events.EventListener.constructor = Casper.Events.EventListener;
Casper.Events.EventListener.prototype = {
    eventType: null,
    handler: null,
    windows: null,
    stateManager: null,
    get windowWatcher() {
        return Components.classes["@mozilla.org/embedcomp/window-watcher;1"]
                        .getService(Components.interfaces.nsIWindowWatcher);
    },
    QueryInterface: function(iid) {
      if (iid.Equals(Components.interfaces.nsIObserver) ||
          iid.Equals(Components.interfaces.nsISupports))
        return this;
      throw Components.results.NS_ERROR_NO_INTERFACE;
    },

    observe: function(subject, topic, data)
    {
        switch(topic) {
        case "domwindowopened":
            domWindow = subject.QueryInterface(Components.interfaces.nsIDOMWindow);
            this.log.debug("domwindowopened "+domWindow);
            domWindow.Casper = Casper;
            this.startNewWindow(domWindow);
            break;
        case "domwindowclosed":
            this.log.debug("domwindowclosed "+domWindow);
            domWindow = subject.QueryInterface(Components.interfaces.nsIDOMWindow);
            this.stopWindow(domWindow);
            delete domWindow.Casper;
            break;
        }
    },
    
    startNewWindow: function(aWindow)
    {
        this.startListeners(aWindow);
        this.windows.push(aWindow);
        if (this.stateManager) {
            this.stateManager.start(aWindow);
        }
    },
    
    stopWindow: function(aWindow)
    {
        this.stopListeners(aWindow);
        this.windows.splice(this.windows.indexOf(aWindow), 1);
        if (this.stateManager) {
            this.stateManager.stop(aWindow);
        }
    },
    
    start: function(aWindow)
    {
        this.log.debug("start listener");
        this.windowWatcher.registerNotification(this);
        this.startNewWindow(aWindow);
    },
    stop: function()
    {
        this.log.debug("stop listener");
        this.windowWatcher.unregisterNotification(this);
        // stop on all windows we've started on
        for (var i = 0; i < this.windows.length; i++) {
            this.stopWindow(this.windows[i]);
        }
        this.windows = [];
    },
    
    addListener: function(name)
    {
        this.log.debug("add listener for "+name);
        this.eventType[name]=1;
    },
    
    startListeners: function(aWindow)
    {
        for (var name in this.eventType) {
            this.log.debug("listen for "+name);
            Casper.Events.factory.get(name).listen(aWindow, this);
        }
    },

    stopListeners: function(aWindow)
    {
        for (var name in this.eventType) {
            this.log.debug("stop listening for "+name);
            Casper.Events.factory.get(name).stop(aWindow, this);
        }
    },
    
    handleEvent: function(event)
    {
        this.log.debug("handleEvent for "+event.type);
        try {
            this.handler.handleEvent(event);
        } catch(e) {
            this.log.exception(e);
        }
    }
}

Casper.Events.currentRecorder = null;
Casper.Events.recorder = function() {
    this.log = Casper.Logging.getLogger('Casper::Events::recorder');
    //this.log.setLevel(Casper.Logging.DEBUG);
    this.listener = new Casper.Events.EventListener(this);
}
Casper.Events.recorder.constructor = Casper.Events.recorder;
Casper.Events.recorder.prototype = {
    recording: false,
    currentTest: null,
    listener: null,

    start: function(aWindow)
    {
        this.log.debug("start recording with window "+aWindow);
        Casper.Events.currentRecorder = this;
        Casper.Events.log.debug("prepare recording");
        try {
            this.recording = true;
            aWindow.focus();
            // insert event listeners on window
            this.currentTest = new Casper.Events.test(aWindow);
            this.listener.start(aWindow);
            Casper.Events.log.debug("start recording");
        } catch(e) { this.log.exception(e); }
    },
    
    stop: function(aWindow)
    {
        try {
            this.recording = false;
            Casper.Events.log.debug("stop recording");
            this.listener.stop();
            Casper.Events.currentRecorder = null;
        } catch(e) { this.log.exception(e); }
        this.log.debug("stop recording with window "+aWindow);
    },
    
    replay: function()
    {
        this.currentTest.replay();
    },
    
    handleEvent: function(event)
    {
        this.currentTest.addEvent(event);
    }
}


