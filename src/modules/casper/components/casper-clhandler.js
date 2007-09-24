/* -*- Mode: JavaScript; tab-width: 8; indent-tabs-mode: nil; c-basic-offset: 4 -*- */
/* Copyright (c) 2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/*
 * -casper commandline handler; starts unittests.
 */

const nsISupports           = Components.interfaces.nsISupports;
const nsICategoryManager    = Components.interfaces.nsICategoryManager;
const nsIComponentRegistrar = Components.interfaces.nsIComponentRegistrar;
const nsICommandLine        = Components.interfaces.nsICommandLine;
const nsICommandLineHandler = Components.interfaces.nsICommandLineHandler;
const nsIFactory            = Components.interfaces.nsIFactory;
const nsIModule             = Components.interfaces.nsIModule;
const nsIWindowWatcher      = Components.interfaces.nsIWindowWatcher;
const nsIObserver           = Components.interfaces.nsIObserver;
/*
 * Classes
 */


const CasperConsoleHandler = {
    params: [],
    onload: null,
    eot: false,
    logfile: null,
    windowHasOpened: false,
    /* nsISupports */
    QueryInterface : function clh_QI(iid) {
        if (iid.equals(nsICommandLineHandler) ||
            iid.equals(nsIObserver) ||
            iid.equals(nsIFactory) ||
            iid.equals(nsISupports))
            return this;

        throw Components.results.NS_ERROR_NO_INTERFACE;
    },

    /* nsICommandLineHandler */

    handle : function clh_handle(cmdLine) {
        try {
            //dump("Capser clh_handle:: Arguments:\n");
            //for (var i=0; i < cmdLine.length; i++) {
            //    dump("  Argument[" + i + "]: " + cmdLine.getArgument(i) + "\n");
            //}
            if (cmdLine.findFlag("casper", false) < 0) {
                return;
            }
            if (cmdLine.findFlag("eot", false) >= 0) {
                cmdLine.handleFlag("eot", false);
                this.eot = true;
            }
            if (cmdLine.findFlag("logfile", false) >= 0) {
                this.logfile = cmdLine.handleFlagWithParam("logfile", false);
            }
            // Now we just grab everything in the command line
            cmdLine.handleFlag("casper", false);
            for (var i=0; i < cmdLine.length; i++) {
                this.params.push(cmdLine.getArgument(i));
            }
            cmdLine.removeArguments(0, cmdLine.length - 1);
            // we need to wait for the main window to startup before we
            // run any tests
            this.windowWatcher.registerNotification(this);
        } catch(e) {
            dump(e+"\n");
        }
    },

    helpInfo : "       -casper <tests>      start unittests.\n"+
               "       -eot                 exit app when tests completed.\n"+
               "       -logfile             save results to this logfile.\n\n"+
               "  Example: -casper test_something.js#mytestcase.childtest\n",

    /* nsIFactory */

    createInstance : function clh_CI(outer, iid) {
        if (outer != null)
            throw Components.results.NS_ERROR_NO_AGGREGATION;

        return this.QueryInterface(iid);
    },

    lockFactory : function clh_lock(lock) {
        /* no-op */
    },

    get windowWatcher() {
        return Components.classes["@mozilla.org/embedcomp/window-watcher;1"]
                        .getService(Components.interfaces.nsIWindowWatcher);
    },
    
    observe: function(subject, topic, data)
    {
        switch(topic) {
        case "domwindowopened":
            try {
                var domWindow = subject.QueryInterface(Components.interfaces.nsIDOMWindow);
                this.windowWatcher.unregisterNotification(this);
                // now we install an event listener and wait for the load event
                var self = this;
                var handler = function(event) {
                    try {
                        domWindow.removeEventListener("load", handler, false);
                        self.handleLoad(event);
                    } catch(e) {
                        dump(e+"\n");
                    }
                }
                domWindow.addEventListener("load", handler, false);
            } catch(e) {
                dump(e+"\n");
            }
            break;
        }
    },
    
    handleLoad: function(event) {
        try {
            if (event.type != "load") return;
            // target is document, currentTarget is the chromeWindow
            // is this a xul window?
            if (event.target.contentType != 'application/vnd.mozilla.xul+xml')
                return;
            var win = event.currentTarget;
            if ('Casper' in event.currentTarget) {
                if (this.params.length > 0) {
                    win.setTimeout(function(w, p, l, e) {
                                       w.Casper.UnitTest.runTestsText(p, l, e);
                                   }, 1000, win, this.params, this.logfile,
                                   this.eot);
                    this.params = [];
                } else {
                    // open the xul test window
                    win.setTimeout(win.Casper.UnitTest.runTestsXUL, 1000);
                }
            }
        } catch(e) {
            dump(e+"\n");
        }
    }
};

const clh_contractID = "@activestate.com/casper/casper-clh;1";
const clh_CID = Components.ID("{C37134CD-A4B0-11DA-BA30-000D935D3368}");
const clh_category = "c-casper";

const CasperConsoleHandlerModule = {
    /* nsISupports */

    QueryInterface : function mod_QI(iid) {
        if (iid.equals(nsIModule) ||
            iid.equals(nsISupports))
            return this;

        throw Components.results.NS_ERROR_NO_INTERFACE;
    },

    /* nsIModule */

    getClassObject : function mod_gch(compMgr, cid, iid) {
        if (cid.equals(clh_CID))
            return CasperConsoleHandler.QueryInterface(iid);

        throw Components.results.NS_ERROR_NOT_REGISTERED;
    },

    registerSelf : function mod_regself(compMgr, fileSpec, location, type) {
        compMgr.QueryInterface(nsIComponentRegistrar);

        compMgr.registerFactoryLocation(clh_CID,
                                        "CasperConsoleHandler",
                                        clh_contractID,
                                        fileSpec,
                                        location,
                                        type);

        var catMan = Components.classes["@mozilla.org/categorymanager;1"]
                               .getService(nsICategoryManager);
        catMan.addCategoryEntry("command-line-handler",
                                clh_category,
                                clh_contractID, true, true);
    },

    unregisterSelf : function mod_unreg(compMgr, location, type) {
        compMgr.QueryInterface(nsIComponentRegistrar);

        compMgr.unregisterFactoryLocation(clh_CID, location);

        var catMan = Components.classes["@mozilla.org/categorymanager;1"]
                               .getService(nsICategoryManager);
        catMan.deleteCategoryEntry("command-line-handler", clh_category);
    },

    canUnload : function (compMgr) {
        return true;
    }
};

/* module initialisation */
function NSGetModule(comMgr, fileSpec) {
    return CasperConsoleHandlerModule;
}
