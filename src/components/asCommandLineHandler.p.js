// Copyright (c) 2005-2006 ActiveState Software Inc.
// See the file LICENSE.txt for licensing information.
// adapted from browser/components/nsBrowserContentHandler.js

const winOptions = 
// #if PLATFORM == "darwin"
  "chrome,dialog=no,all";
// #else
  "chrome,all";
// #endif

var gInfoSvc = null;

function shouldLoadURI(aURI) {
  if (aURI && !aURI.schemeIs("chrome"))
    return true;
	
  log.warn("*** Preventing external load of chrome: URI into window\n");
  log.warn("    Use -chrome <uri> instead\n");
  return false;
}

function resolveURIInternal(aCmdLine, aArgument) {
  var uri = aCmdLine.resolveURI(aArgument);

  if (!(uri instanceof Components.interfaces.nsIFileURL)) {
    return uri;
  }

  try {
    if (uri.file.exists())
      return uri;
  }
  catch (e) {
    Components.utils.reportError(e);
  }

  // We have interpreted the argument as a relative file URI, but the file
  // doesn't exist. Try URI fixup heuristics: see bug 290782.
 
  try {
    var urifixup = Components.classes["@mozilla.org/docshell/urifixup;1"]
                             .getService(Components.interfaces.nsIURIFixup);

    uri = urifixup.createFixupURI(aArgument, 0);
  }
  catch (e) {
    Components.utils.reportError(e);
  }

  return uri;
}

function komodoPlatformInit() {
    try {
        const loader = Components.classes["@mozilla.org/moz/jssubscript-loader;1"]
                             .getService(Components.interfaces.mozIJSSubScriptLoader);
        loader.loadSubScript('chrome://komodo/content/library/logging.js');
    } catch(e) {
        dump(e+"\n");
    }
    var initSvc = Components.classes["@activestate.com/koInitService;1"].
                  getService(Components.interfaces.koIInitService);
    try {
	// upgrade must occure before *ANYTHING*
        initSvc.upgradeUserSettings();
    } catch(e) {
        log.exception(e, "***Komodo Initialization Service failed in upgradeUserSettings***\n");
    }
    try {
        initSvc.installSamples(false);
    } catch(e) {
        log.exception(e, "***Komodo Initialization Service failed in installSamples***\n");
    }
    try {
        initSvc.setPlatformErrorMode();
    } catch(e) {
        log.exception(e, "***Komodo Initialization Service failed in setPlatformErrorMode***\n");
    }
    try {
        initSvc.setEncoding();
    } catch(e) {
        log.exception(e, "***Komodo Initialization Service failed in setEncoding***\n");
    }
    try {
        initSvc.initProcessUtils();
    } catch(e) {
        log.exception(e, "***Komodo Initialization Service failed in initProcessUtils***\n");
    }
    try {
        initSvc.initExtensions();
    } catch(e) {
        log.exception(e, "***Komodo Initialization Service failed in initExtensions***\n");
    }
}

function openWindow(parent, url, target, features, args) {
    var wwatch = Components.classes["@mozilla.org/embedcomp/window-watcher;1"]
            .getService(Components.interfaces.nsIWindowWatcher);
    return wwatch.openWindow(parent, url, target, features, args);
}

// Duplicate of windowManager.js:windowManager_getMainWindow.
function getMostRecentWindow(aType) {
    var wm = Components.classes["@mozilla.org/appshell/window-mediator;1"]
            .getService(Components.interfaces.nsIWindowMediator);
    return wm.getMostRecentWindow(aType);
}

/* A modified copy of dialogs.js::dialog_internalError() to make
 * window launching work here.
 */
function _internalError(error, text)
{
    if (typeof(error) == 'undefined' || error == null)
        throw("Must specify 'error' argument to _internalError().");
    if (typeof(text) == 'undefined' || text == null)
        throw("Must specify 'text' argument to _internalError().");

    // Show the dialog.
    var args =  Components.classes["@mozilla.org/supports-array;1"]
           .createInstance(Components.interfaces.nsISupportsArray);
    var errorObj = Components.classes["@mozilla.org/supports-string;1"]
           .createInstance(Components.interfaces.nsISupportsString);
    errorObj.data = error;
    args.AppendElement(errorObj);
    var textObj = Components.classes["@mozilla.org/supports-string;1"]
            .createInstance(Components.interfaces.nsISupportsString);
    textObj.data = text;
    args.AppendElement(textObj);
    openWindow(null,
               "chrome://komodo/content/dialogs/internalError.xul",
               "_blank",
               "chrome,modal,titlebar",
               args);
}

var nsKomodoCommandLineHandler = {
  mChromeURL : null,

  get chromeURL() {
    if (this.mChromeURL) {
      return this.mChromeURL;
    }

    this.mChromeURL = "chrome://komodo/content";
    return this.mChromeURL;
  },

  /* nsISupports */
  QueryInterface : function dch_QI(iid) {
    if (!iid.equals(Components.interfaces.nsISupports) &&
        !iid.equals(Components.interfaces.nsICommandLineHandler) &&
        !iid.equals(Components.interfaces.nsIFactory))
      throw Components.errors.NS_ERROR_NO_INTERFACE;

    return this;
  },

  /* nsICommandLineHandler */
  handle : function dch_handle(cmdLine) {
    var urilist = [];

    try {
      var ar;
      while ((ar = cmdLine.handleFlagWithParam("url", false))) {
        urilist.push(resolveURIInternal(cmdLine, ar));
      }
    }
    catch (e) {
      Components.utils.reportError(e);
    }

    var count = cmdLine.length;

    for (var i = 0; i < count; ++i) {
      var curarg = cmdLine.getArgument(i);
      if (curarg.match(/^-/)) {
        Components.utils.reportError("Warning: unrecognized command line flag " + curarg + "\n");
        // To emulate the pre-nsICommandLine behavior, we ignore
        // the argument after an unrecognized flag.
        ++i;
      } else {
        try {
          urilist.push(resolveURIInternal(cmdLine, curarg));
        }
        catch (e) {
          Components.utils.reportError("Error opening URI '" + curarg + "' from the command line: " + e + "\n");
        }
      }
    }

    var koWin = getMostRecentWindow("Komodo");
    if (urilist.length) {
      var obsvc = Components.classes["@mozilla.org/observer-service;1"].
            getService(Components.interfaces.nsIObserverService);
      var speclist = [];
      for (var uri in urilist) {
        if (shouldLoadURI(urilist[uri]))
          speclist.push(urilist[uri].spec);
      }
      if (speclist.length) {
        if (speclist.length == 1) {
          speclist = speclist[0];
        } else {
          speclist = speclist.join("|");
        }
        if (!cmdLine.preventDefault && !koWin) {
          // if we couldn't load it in an existing window, open a new one
          var args =  Components.classes["@mozilla.org/supports-array;1"]
                 .createInstance(Components.interfaces.nsISupportsArray);
  
          var paramBlock = 
              Components.classes["@mozilla.org/embedcomp/dialogparam;1"].
              createInstance(Components.interfaces.nsIDialogParamBlock);
          paramBlock.SetString(0, speclist);
          args.AppendElement(paramBlock);

          openWindow(null, this.chromeURL, "_blank", winOptions, args);
          cmdLine.preventDefault = true; // stop the browser from handling this also
          return;
        }
        try {
            obsvc.notifyObservers(this, 'open-url', speclist);
        } catch(e) { /* exception if no listeners */ }
      }

    }
    else if (!cmdLine.preventDefault && !koWin) {
      openWindow(null, this.chromeURL, "_blank", winOptions);
      cmdLine.preventDefault = true; // stop the browser from handling this also
    }
  },

  // XXX localize me... how?
  helpInfo : "Usage: komodo [-flags] [<url>]\n",

  /* nsIFactory */
  createInstance: function dch_CI(outer, iid) {
    if (outer != null)
      throw Components.results.NS_ERROR_NO_AGGREGATION;

    komodoPlatformInit();
    return this.QueryInterface(iid);
  },
    
  lockFactory : function dch_lock(lock) {
    /* no-op */
  }
};

const dch_contractID = "@activestate.com/komodo/final-clh;1";
const dch_CID = Components.ID("{07DCEAC7-31F6-11DA-BC61-000D935D3368}");

var Module = {
  /* nsISupports */
  QueryInterface: function mod_QI(iid) {
    if (iid.equals(Components.interfaces.nsIModule) ||
        iid.equals(Components.interfaces.nsISupports))
      return this;

    throw Components.results.NS_ERROR_NO_INTERFACE;
  },

  /* nsIModule */
  getClassObject: function mod_getco(compMgr, cid, iid) {
    if (cid.equals(dch_CID))
      return nsKomodoCommandLineHandler.QueryInterface(iid);

    throw Components.results.NS_ERROR_NO_INTERFACE;
  },
    
  registerSelf: function mod_regself(compMgr, fileSpec, location, type) {
    var compReg =
      compMgr.QueryInterface( Components.interfaces.nsIComponentRegistrar );
    compReg.registerFactoryLocation( dch_CID,
                                     "nsKomodoCommandLineHandler",
                                     dch_contractID,
                                     fileSpec,
                                     location,
                                     type );

    var catMan = Components.classes["@mozilla.org/categorymanager;1"]
                           .getService(Components.interfaces.nsICategoryManager);

    catMan.addCategoryEntry("command-line-handler",
                            "ko-default",
                            dch_contractID, true, true);
  },
    
  unregisterSelf : function mod_unregself(compMgr, location, type) {
    var compReg = compMgr.QueryInterface(Components.interfaces.nsIComponentRegistrar);
    compReg.unregisterFactoryLocation(dch_CID, location);

    var catMan = Components.classes["@mozilla.org/categorymanager;1"]
                           .getService(Components.interfaces.nsICategoryManager);

    catMan.deleteCategoryEntry("command-line-handler",
                               "ko-default", true);
  },

  canUnload: function(compMgr) {
    return true;
  }
};

// NSGetModule: Return the nsIModule object.
function NSGetModule(compMgr, fileSpec) {
  return Module;
}
