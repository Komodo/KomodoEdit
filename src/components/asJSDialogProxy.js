// Copyright (c) 2000-2006 ActiveState Software Inc.
// See the file LICENSE.txt for licensing information.

const DEBUG = false; /* set to true to enable debug messages */

const DIALOGPROXY_CONTRACTID     = "@activestate.com/asDialogProxy;1";
const DIALOGPROXY_CID        = Components.ID("{57002286-C22C-4e42-BCFC-DE91AF24B5CA}");
const APPSHELL_SERV_CONTRACTID  = "@mozilla.org/appshell/appShellService;1";

const nsIAppShellService    = Components.interfaces.nsIAppShellService;
const nsISupports           = Components.interfaces.nsISupports;
const nsIFactory            = Components.interfaces.nsIFactory;
const asIDialogProxy         = Components.interfaces.asIDialogProxy;
const nsIInterfaceRequestor = Components.interfaces.nsIInterfaceRequestor
const nsIDOMWindow          = Components.interfaces.nsIDOMWindow;


function asDialogProxy()
{
    this.mParentWindow = null;
    this.loggingSvc = Components.classes["@activestate.com/koLoggingService;1"].
                    getService(Components.interfaces.koILoggingService);
    this.log = this.loggingSvc.getLogger('asdialogproxy');
    this.lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
                        getService(Components.interfaces.koILastErrorService);
}

asDialogProxy.prototype = {
  init: function(parent) {
    this.mParentWindow = parent;
  },
    
  _getParentWindow: function() {
    /* if we can get the window from the window mediator, just use that,
       otherwise, fallback to the old behaviour, which always got the
       main komodo window (not exactly what we would want)
    */
    var wm = Components.classes["@mozilla.org/appshell/window-mediator;1"]
                    .getService(Components.interfaces.nsIWindowMediator);
    win = wm.getMostRecentWindow(null);
    if (win) return win;
    /* This is just paranoia (--trentm)  the above should always work, but
      leave the old tested code in place for now. */
    var parent=null;
    try {
      if (typeof(window) == "object" && window != null) {
        parent = window;
      } else if (this.mParentWindow) {
        return this.mParentWindow;
      } else {
        try {
          var appShellService = Components.classes[APPSHELL_SERV_CONTRACTID].getService(nsIAppShellService);
          parent = appShellService.hiddenDOMWindow;
          parent.oldfocus = parent.focus;
          parent.focus = function(){};
        } catch(ex) {
          debug("Can't get parent.  xpconnect hates me so we can't get one from the appShellService.\n");
          debug(ex + "\n");
        }
      }
    } catch(ex) { debug("no window access\n"); }
    if (!this.mParentWindow)
      this.mParentWindow = parent;
    return parent;
  },

  alert: function(prompt) {
      return this.alertEx(prompt, true, true, "OK", "Cancel");
  },
  
  alertEx: function(prompt, okIsDefault, hideCancel, okLabel, cancelLabel) {
    var parent = this._getParentWindow();
    try {
        if (typeof(prompt) == 'undefined') prompt = null;
        if (typeof(response) == 'undefined') response = null;
        if (typeof(text) == 'undefined') text = null;
        if (typeof(title) == 'undefined') title = null;
        if (typeof(doNotAskPref) == 'undefined') doNotAskPref = null;
    
        // Show the dialog.
        var obj = new Object();
        obj.prompt = prompt;
        obj.response = response;
        obj.text = text;
        obj.title = title;
        obj.doNotAskUI = false;
        parent.openDialog("chrome://komodo/content/dialogs/okCancel.xul",
                          "_blank",
                          "chrome,modal,titlebar",
                          obj);
    
        return obj.response;      
    } catch(ex) { dump("unable to open alert dialog\n" + ex + "\n"); }

    return "";
  },

  authenticate: function(title, server, prompt, loginname, allowAnonymous, allowPersist) {
    /* NOTE: if you change this usage, also change it in window_functions.js */
    var parent = this._getParentWindow();
    try {
        var obj = new Object();
        obj.title = title;
        obj.server = server;
        obj.prompt = prompt;
        obj.username = loginname;
        obj.allowAnonymous = allowAnonymous;
        obj.allowPersist = allowPersist;
        parent.openDialog("chrome://komodo/content/dialogs/authenticate.xul",
                      "_blank",
                      "chrome,modal,titlebar",
                      obj);
        if (obj.retval == "Login") {
            return obj.username + ":" + obj.password;
        }
    } catch(ex) { dump("unable to open auth dialog\n" + ex + "\n"); }

    return "";
  },

  prompt: function(prompt, value, okLabel, cancelLabel) {
    var parent = this._getParentWindow();
    try {
        if (typeof(prompt) == 'undefined') prompt = null;
        if (typeof(label) == 'undefined') label = null;
        if (typeof(value) == 'undefined') value = null;
        if (typeof(title) == 'undefined') title = null;
        if (typeof(mruName) == 'undefined') mruName = null;
        if (typeof(validator) == 'undefined') validator = null;
        if (typeof(multiline) == 'undefined') multiline = null;
        if (typeof(screenX) == 'undefined') screenX = null;
        if (typeof(screenY) == 'undefined') screenY = null;
        if (mruName && multiline) {
            log.warn("Cannot use both 'mruName' and 'multiline' on prompt "+
                     "dialogs. 'mruName' will be ignored.");
            mruName = null;
        }
    
        var obj = new Object();
        obj.prompt = prompt;
        obj.label = label;
        obj.value = value;
        obj.title = title;
        obj.mruName = mruName;
        obj.validator = validator;
        obj.multiline = multiline;
        obj.screenX = screenX;
        obj.screenY = screenY;
        parent.openDialog("chrome://komodo/content/dialogs/prompt.xul",
                          "_blank",
                          "chrome,modal,titlebar",
                          obj);
        if (obj.retval == "OK") {
            return obj.value;
        } else {
            return null;
        }
    } catch(ex) { dump("unable to open prompt dialog\n" + ex + "\n"); }

    return "";
  },
  
  open: function(url, name, flags, obj) {
      var parent = this._getParentWindow();
      try {
          return parent.open(url, name, flags, obj);
      } catch (e) {
          this.log.error(e);
          this.lastErrorSvc.setLastError(Components.results.NS_ERROR_FAILURE, e);
          //XXX Should we re-raise, as in eval_()?
      }
      return null;
  },
  
  openDialog: function(url, name, flags, obj) {
      var parent = this._getParentWindow();
      try {
          return parent.openDialog(url, name, flags, obj);
      } catch (e) {
          this.log.error(e);
          this.lastErrorSvc.setLastError(Components.results.NS_ERROR_FAILURE, e);
          //XXX Should we re-raise, as in eval_()?
      }
      return null;
  },

  eval_: function(window, code) {
      try {
          return window.eval(code);
      } catch (e) {
          this.log.error("THROWING" + e);
          this.lastErrorSvc.setLastError(Components.results.NS_ERROR_FAILURE, e);
          throw Components.results.NS_ERROR_FAILURE;
      }
      return null;
  },

  QueryInterface: function(iid) {
    if (!iid.equals(asIDialogProxy) &&
        !iid.equals(nsISupports))
        throw Components.results.NS_ERROR_NO_INTERFACE;
    return this;
  }
}

/* module foo */

var dialogProxyModule = new Object();

dialogProxyModule.registerSelf =
function (compMgr, fileSpec, location, type)
{
    compMgr = compMgr.QueryInterface(Components.interfaces.nsIComponentRegistrar);
    compMgr.registerFactoryLocation(DIALOGPROXY_CID, 
                                "JS Dialog Proxy Component",
                                DIALOGPROXY_CONTRACTID, 
                                fileSpec, 
                                location,
                                type);
}

dialogProxyModule.getClassObject =
function (compMgr, cid, iid) {
    if (!cid.equals(DIALOGPROXY_CID))
        throw Components.results.NS_ERROR_NO_INTERFACE;
    
    if (!iid.equals(Components.interfaces.nsIFactory))
        throw Components.results.NS_ERROR_NOT_IMPLEMENTED;
    
    return dialogProxyFactory;
}

dialogProxyModule.canUnload =
function(compMgr)
{
    debug("Unloading component.");
    return true;
}
    
/* factory object */
var dialogProxyFactory = new Object();

dialogProxyFactory.createInstance =
function (outer, iid) {
    //debug("CI: " + iid);
    //debug("IID:" + asIDialogProxy);
    if (outer != null)
        throw Components.results.NS_ERROR_NO_AGGREGATION;

    return (new asDialogProxy()).QueryInterface(iid);
}

/* entrypoint */
function NSGetModule(compMgr, fileSpec) {
    return dialogProxyModule;
}
