/* components defined in this file */
const CLINE_SERVICE_CTRID =
    "@mozilla.org/commandlinehandler/general-startup;1?type=jslib";
const CLINE_SERVICE_CID =
    Components.ID("{b9d7bca5-ddc9-4151-b1cd-f33347addf9b}");

/* components defined in this file */
const CLINE_SERVICE_JSLIBLIVE_CTRID =
    "@mozilla.org/commandlinehandler/general-startup;1?type=jsliblive";
const CLINE_SERVICE_JSLIBLIVE_CID =
    Components.ID("{a805c0d9-8fd9-473f-a0c6-020dd260aa1d}");

const JSLIBCNT_HANDLER_CONTRACTID =
    "@mozilla.org/uriloader/content-handler;1?type=x-application-jslib";
const JSLIBCNT_HANDLER_CID =
    Components.ID("{764a1404-3ac6-4d66-bf7e-a1c5fe1dccd0}");

const JSLIBPROT_HANDLER_CONTRACTID =
    "@mozilla.org/network/protocol;1?name=jslib";
const JSLIBPROT_HANDLER_CID =
    Components.ID("{119f6754-ba12-4aed-b3ee-d409895e77ba}");

/* components used by this file */
const ASS_CONTRACTID =
    "@mozilla.org/appshell/appShellService;1";

const MEDIATOR_CONTRACTID =
    "@mozilla.org/appshell/window-mediator;1";

const CATMAN_CTRID = "@mozilla.org/categorymanager;1";

const STANDARDURL_CONTRACTID =
    "@mozilla.org/network/standard-url;1";

const IOSERVICE_CONTRACTID = 
    "@mozilla.org/network/io-service;1";


/* interafces used in this file */
const nsIWindowMediator  = Components.interfaces.nsIWindowMediator;
const nsICmdLineHandler  = Components.interfaces.nsICmdLineHandler;
const nsICategoryManager = Components.interfaces.nsICategoryManager;
const nsIContentHandler  = Components.interfaces.nsIContentHandler;
const nsISupports        = Components.interfaces.nsISupports;
const nsIURI             = Components.interfaces.nsIURI;
const nsIStandardURL     = Components.interfaces.nsIStandardURL;
const nsIChannel         = Components.interfaces.nsIChannel;
const nsIProtocolHandler = Components.interfaces.nsIProtocolHandler;
const nsIRequest         = Components.interfaces.nsIRequest;
const nsIIOService       = Components.interfaces.nsIIOService;
const nsIAppShellService = Components.interfaces.nsIAppShellService;


/* Command Line handler service */
function CLineService() {}

CLineService.prototype.commandLineArgument = "-jslib";
CLineService.prototype.prefNameForStartup = "general.startup.jslib";
CLineService.prototype.chromeUrlForTask = "chrome://jslib/content/";
CLineService.prototype.helpText = "Start jsLib";
CLineService.prototype.handlesArgs = true;
CLineService.prototype.defaultArgs = "";
CLineService.prototype.openWindowWithArgs = true;

/* factory for command line handler service (CLineService) */
var CLineFactory = new Object;

CLineFactory.createInstance =
function clf_create (outer, iid) 
{
  if (outer != null)
      throw Components.results.NS_ERROR_NO_AGGREGATION;

  if (!iid.equals(nsICmdLineHandler) && !iid.equals(nsISupports))
      throw Components.results.NS_ERROR_INVALID_ARG;

  return new CLineService();
}

function CLineJSLiveService() {}

CLineJSLiveService.prototype.commandLineArgument = "-jsliblive";
CLineJSLiveService.prototype.prefNameForStartup = "general.startup.jsliblive";
CLineJSLiveService.prototype.chromeUrlForTask = "chrome://jsliblive/content/";
CLineJSLiveService.prototype.helpText = "Start jsLib Live";
CLineJSLiveService.prototype.handlesArgs = true;
CLineJSLiveService.prototype.defaultArgs = "";
CLineJSLiveService.prototype.openWindowWithArgs = true;

var CLineJSLiveFactory = new Object;

CLineJSLiveFactory.createInstance =
function clf_create (outer, iid) 
{
  if (outer != null)
      throw Components.results.NS_ERROR_NO_AGGREGATION;

  if (!iid.equals(nsICmdLineHandler) && !iid.equals(nsISupports))
      throw Components.results.NS_ERROR_INVALID_ARG;

  return new CLineJSLiveService();
}

/* x-application-jslib content handler */
function jslibContentHandler () {}

jslibContentHandler.prototype.QueryInterface =
function (iid)
{
  if (!iid.equals(nsIContentHandler))
      throw Components.results.NS_ERROR_NO_INTERFACE;

  return this;
}

jslibContentHandler.prototype.handleContent =
function (contentType, windowTarget, request, aRemovedArg)
{
  // backwards compatability for pre 1.5 releases
  if (aRemovedArg) request = aRemovedArg;

  var e;
  var channel = request.QueryInterface(nsIChannel);
    
  var windowManager =
      Components.classes[MEDIATOR_CONTRACTID].getService(nsIWindowMediator);

  var w = windowManager.getMostRecentWindow("navigator:browser");

  if (w) {
    var url = "http://jslib.mozdev.org/";
    var uri = channel.URI;
    var cmd = uri.spec.replace(/^jslib|:|\//g, "");
    switch (cmd)
    {
      case "about":
      const cURL = "chrome://jslib/content/jslib/content/aboutDialog.xul";
      w.openDialog(cURL, "_blank", "chrome,dialog=no,resizable=no,centerscreen");
      //closeIf(w);
      return;
          
      case "splash":
      case "version":
      const jURL = "chrome://jslib/content/";
      w.openDialog(jURL, "_blank", "chrome,dialog=no,resizable=no");
      //closeIf(w);
      return;
          
      case "get":
      case "inst":
      url += "installation.html";
      break;
          
      case "help":
      url += "help.html";
      break;
          
      case "bugs":
      url += "bugs.html";
      break;
          
      case "list":
      url += "list.html";
      break;

      case "docs":
      url += "doc_index.html";
      break;

      case "clients":
      url += "clients.html";
      break;

      case "modules":
      url += "modules.html";
      break;

      case "source":
      url = "http://www.mozdev.org/source/browse/jslib/";
      break;

      case "io":
      case "debug":
      case "install":
      case "rdf":
      case "network":
      case "sound":
      case "utils":
      case "xul":
      url += "libraries/"+cmd+"/"+cmd+".html";
      break;

      case "remotefile":
      url = "http://jslib.mozdev.org/libraries/network/remotefile.html";
      break;

      case "file":
      url = "http://jslib.mozdev.org/libraries/io/file.js.html";
      break;

      case "chromefile":
      url = "http://jslib.mozdev.org/libraries/io/chromeFile.js.html";
      break;

      case "dir":
      url = "http://jslib.mozdev.org/libraries/io/dir.js.html";
      break;

      case "fileutils":
      url = "http://jslib.mozdev.org/libraries/io/fileutils.js.html";
      break;

      case "dirutils":
      url = "http://jslib.mozdev.org/libraries/io/dirUtils.js.html";
      break;

      case "uninstall":
      url = "http://jslib.mozdev.org/libraries/install/uninstall.html";
      break;

      case "autoupdate":
      url = "http://jslib.mozdev.org/libraries/install/autoupdate.html";
      break;

      case "zip":
      url = "http://jslib.mozdev.org/libraries/zip/zip.js.html";
      break;

      case "prefs":
      url = "http://jslib.mozdev.org/libraries/utils/prefs.html";
      break;

      case "packageinfo":
      url = "http://jslib.mozdev.org/libraries/utils/packageinfo.html";
      break;

      case "date":
      url = "http://jslib.mozdev.org/libraries/utils/date.html";
      break;

      case "samples.file":
      const fURL = "chrome://jslib/content/samples/file.xul";
      w.openDialog(fURL, "_blank", "chrome,dialog=no");
      //closeIf(w);
      return;

      case "samples.remotefile":
      const rURL = "chrome://jslib/content/samples/remotefile.xul";
      w.openDialog(rURL, "_blank", "chrome,dialog=no");
      //closeIf(w);
      return;

      case "debug.on":
      jslibDebugOn(w);
      closeIf(w);
      return;
          
      case "debug.off":
      jslibDebugOff(w);
      closeIf(w);
      return;
          
    }
    w.focus();
    w.loadURI(url);
  } else {
    var ass =
        Components.classes[ASS_CONTRACTID].getService(nsIAppShellService);
    w = ass.hiddenDOMWindow;

    var args = new Object ();
    args.url = "http://jslib.mozdev.org/";

    w.openDialog("chrome://navigator/content/", "_blank",
                 "chrome,menubar,toolbar,status,resizable,dialog=no",
                 args);
  }
}

function closeIf (w)
{
  if (!w.document._content)
    w.close();
}

function jslibDebugOn (w)
{
  if (!w)
    return;

  w.jslib.init(w);
  w.jslibTurnDumpOn();
  w.jslibTurnStrictOn();
}

function jslibDebugOff (w)
{
  if (!w)
    return;

  w.jslib.init(w);
  w.jslibTurnDumpOff();
  w.jslibTurnStrictOff();
}

/* content handler factory object (jslibContentHandler) */
var jslibContentHandlerFactory = new Object();

jslibContentHandlerFactory.createInstance =
function (outer, iid)
{
  if (outer != null)
    throw Components.results.NS_ERROR_NO_AGGREGATION;

  if (!iid.equals(nsIContentHandler) && !iid.equals(nsISupports))
    throw Components.results.NS_ERROR_INVALID_ARG;

  return new jslibContentHandler();
}

/* jslib protocol handler component */
function jslibProtocolHandler() {}

jslibProtocolHandler.prototype.scheme = "jslib";
jslibProtocolHandler.prototype.defaultPort = 4100;
jslibProtocolHandler.prototype.protocolFlags = 
                   nsIProtocolHandler.URI_NORELATIVE |
                   nsIProtocolHandler.ALLOWS_PROXY;

jslibProtocolHandler.prototype.allowPort =
function (port, scheme) { return false; }

jslibProtocolHandler.prototype.newURI =
function (spec, charset, baseURI)
{
  var cls = Components.classes[STANDARDURL_CONTRACTID];
  var url = cls.createInstance(nsIStandardURL);
  url.init(nsIStandardURL.URLTYPE_STANDARD, 4100, spec, charset, baseURI);

  return url.QueryInterface(nsIURI);
}

jslibProtocolHandler.prototype.newChannel =
function (URI)
{
  ios = Components.classes[IOSERVICE_CONTRACTID].getService(nsIIOService);
  if (!ios.allowPort(URI.port, URI.scheme))
      throw Components.results.NS_ERROR_FAILURE;

  return new BogusChannel (URI);
}

/* protocol handler factory object (jslibProtocolHandler) */
var jslibProtocolHandlerFactory = new Object();

jslibProtocolHandlerFactory.createInstance =
function (outer, iid)
{
  if (outer != null)
    throw Components.results.NS_ERROR_NO_AGGREGATION;

  if (!iid.equals(nsIProtocolHandler) && !iid.equals(nsISupports))
    throw Components.results.NS_ERROR_INVALID_ARG;

  return new jslibProtocolHandler();
}

/* bogus channel used by the JSLIBProtocolHandler */
function BogusChannel (URI)
{
  this.URI = URI;
  this.originalURI = URI;
}

BogusChannel.prototype.QueryInterface =
function (iid)
{
  if (!iid.equals(nsIChannel) && !iid.equals(nsIRequest) &&
      !iid.equals(nsISupports))
      throw Components.results.NS_ERROR_NO_INTERFACE;

  return this;
}

/* nsIChannel */
BogusChannel.prototype.loadAttributes = null;
BogusChannel.prototype.contentType = "x-application-jslib";
BogusChannel.prototype.contentLength = 0;
BogusChannel.prototype.owner = null;
BogusChannel.prototype.loadGroup = null;
BogusChannel.prototype.notificationCallbacks = null;
BogusChannel.prototype.securityInfo = null;

BogusChannel.prototype.open =
BogusChannel.prototype.asyncOpen =
function () { throw Components.results.NS_ERROR_NOT_IMPLEMENTED; }

BogusChannel.prototype.asyncOpen =
function (observer, ctxt)
{
  observer.onStartRequest (this, ctxt);
}

BogusChannel.prototype.asyncRead =
function (listener, ctxt)
{
  return listener.onStartRequest (this, ctxt);
}

/* nsIRequest */
BogusChannel.prototype.isPending =
function () { return true; }

BogusChannel.prototype.status = Components.results.NS_OK;

BogusChannel.prototype.cancel =
function (status)
{
  this.status = status;
}

BogusChannel.prototype.suspend =
BogusChannel.prototype.resume =
function ()
{
  throw Components.results.NS_ERROR_NOT_IMPLEMENTED;
}

/*****************************************************************************/

var Module = new Object();

Module.registerSelf =
function (cm, fileSpec, location, type)
{
    // debug("*** Registering -jslib handler.\n");
    
    cm = cm.QueryInterface(Components.interfaces.nsIComponentRegistrar);

    cm.registerFactoryLocation(CLINE_SERVICE_CID,
                               "jsLib CommandLine Service",
                               CLINE_SERVICE_CTRID, 
                               fileSpec,
                               location, 
                               type);

    cm.registerFactoryLocation(CLINE_SERVICE_JSLIBLIVE_CID,
                               "jsLibLive CommandLine Service",
                               CLINE_SERVICE_JSLIBLIVE_CTRID,
                               fileSpec,
                               location, 
                               type);

    catman = Components.classes[CATMAN_CTRID].getService(nsICategoryManager);

    catman.addCategoryEntry("command-line-argument-handlers",
                            "jslib command line handler",
                            CLINE_SERVICE_CTRID, true, true);

    catman.addCategoryEntry("command-line-argument-handlers",
                            "jsliblive command line handler",
                            CLINE_SERVICE_JSLIBLIVE_CTRID, true, true);

    // debug("*** Registering x-application-jslib handler.\n");
    cm.registerFactoryLocation(JSLIBCNT_HANDLER_CID,
                               "jsLib Content Handler",
                               JSLIBCNT_HANDLER_CONTRACTID, 
                               fileSpec,
                               location, 
                               type);

    // debug("*** Registering jslib protocol handler.\n");
    cm.registerFactoryLocation(JSLIBPROT_HANDLER_CID,
                               "jsLib protocol handler",
                               JSLIBPROT_HANDLER_CONTRACTID, 
                               fileSpec, 
                               location,
                               type);

}

Module.unregisterSelf =
function(cm, fileSpec, location)
{
    cm = cm.QueryInterface(Components.interfaces.nsIComponentRegistrar);

    cm.unregisterFactoryLocation(CLINE_SERVICE_CID, fileSpec);
    catman = Components.classes[CATMAN_CTRID].getService(nsICategoryManager);
    catman.deleteCategoryEntry("command-line-argument-handlers",
                                CLINE_SERVICE_CTRID, true);
}

Module.getClassObject =
function (cm, cid, iid) 
{
    if (cid.equals(CLINE_SERVICE_CID))
        return CLineFactory;

    if (cid.equals(CLINE_SERVICE_JSLIBLIVE_CID))
        return CLineJSLiveFactory;

    if (cid.equals(JSLIBCNT_HANDLER_CID))
        return jslibContentHandlerFactory;

    if (cid.equals(JSLIBPROT_HANDLER_CID))
        return jslibProtocolHandlerFactory;
    
    if (!iid.equals(Components.interfaces.nsIFactory))
        throw Components.results.NS_ERROR_NOT_IMPLEMENTED;

    throw Components.results.NS_ERROR_NO_INTERFACE;
    
}

Module.canUnload =
function(cm) { return true; }

/* entrypoint */
function NSGetModule(cm, fileSpec) { return Module; }
