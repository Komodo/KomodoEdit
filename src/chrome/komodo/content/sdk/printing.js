/* Copyright (c) 2000-2013 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/**
 * Printing APIs -- stolen and adapted from mailWindowOverlay.js
 *
 */
const {Cc, Ci, Cu, Cr} = require("chrome");

var _gBrowserLoadListener = null;

const log = require("ko/logging").getLogger("printing");
const PrintUtils = window.PrintUtils;
Cu.import("resource://gre/modules/XPCOMUtils.jsm");

// Get window/KO
var _window;
try
{
    _window = winUtils.getToplevelWindow(window);
}
catch (e)
{
    log.debug("getTopLevelWindow failed, falling back on window mediator");
    
    var wm = Cc["@mozilla.org/appshell/window-mediator;1"].getService(Ci.nsIWindowMediator);
    let windows = wm.getEnumerator("Komodo");
    while (windows.hasMoreElements()) {
        _window = windows.getNext().QueryInterface(Ci.nsIDOMWindow);
    }
}

var ko = _window.ko;

function _initPrintSettings() {
    if (!PrintUtils._gOrigGetPrintSettings) {
        // Replace the PrintUtils method with our own function, one that
        // customizes the print settings according to the users preference.
        PrintUtils._gOrigGetPrintSettings = PrintUtils.getPrintSettings;
        PrintUtils.getPrintSettings = function() {
            /** @type {Components.interfaces.nsIPrintSettings} */
            var settings = PrintUtils._gOrigGetPrintSettings();
            // Customize it.
            settings.headerStrRight = ""; // Never print the URL.
            var prefs = Cc['@activestate.com/koPrefService;1']
                          .getService(Ci.koIPrefService)
                          .prefs;
            if (!prefs.getBooleanPref("printHeaderFilepath")) {
                settings.headerStrLeft = "";
            }
            if (!prefs.getBooleanPref("printFooterPageNumber")) {
                settings.footerStrLeft = "";
            }
            if (!prefs.getBooleanPref("printFooterTimeStamp")) {
                settings.footerStrRight = "";
            }
            return settings;
        }
    }
}

exports.printPreview = function(view, preview, tofile, selectionOnly)
{
    _initPrintSettings();
    window.openDialog("chrome://komodo/content/printPreview.xul",
                      "Komodo:PrintPreview",
                      "chrome,all",
                      view, preview, tofile, selectionOnly
                      );
}

exports.browserPrintPreview = function(evt)
{
    try {
        var browser = document.getElementById("printSource");
        browser.removeEventListener("load", _gBrowserLoadListener, true);
        PrintUtils.printPreview({
            getPrintPreviewBrowser: function() { return document.getElementById("printBrowser"); },
            getSourceBrowser: function() { return browser },
            getNavToolbox: function() { return document.getElementById("printPreviewDeck"); },
            onEnter: function() {
                document.getElementById("printPreviewDeck").setAttribute("selectedIndex",1);
                window.sizeToContent();
            },
            onExit: function() { window.close(); },
        });
    } catch(e) { log.exception(e); }
}

exports.browserPrint = function()
{
    try {
        var browser = document.getElementById("printBrowser");
        browser.removeEventListener("load", _gBrowserLoadListener, true);
        PrintUtils.print();
    } catch(e) { log.exception(e); }
}

exports.print = function(view, preview, tofile, selectionOnly)
{
    try {
        _initPrintSettings();
        var lang = view.koDoc.languageObj;
        var schemeService = Cc['@activestate.com/koScintillaSchemeService;1']
                              .getService();
        var outputFile;
        if (typeof(tofile) == 'undefined') {
            tofile = false;
        }
        var forceColor = false;
        if (tofile) {
            forceColor = true;
        }
        if (typeof(selectionOnly) == 'undefined') {
            selectionOnly = false;
        }
        if (tofile) {
            var newname = view.koDoc.displayPath;
            var os = Cc['@activestate.com/koOs;1'].getService();
            if (view.koDoc.isUntitled) {
                newname = os.path.realpath(os.path.join('.', newname));
            }
            newname = newname + '.html';
            var fname = ko.filepicker.saveFile(
                        os.path.dirname(newname), /* default directory */
                        newname, /* default name - knows about dirs */
                        "Save '"+os.path.basename(newname)+"' As...", "HTML");
            if (!fname) return false;
        } else {
            var tmpFileSvc = Cc["@activestate.com/koFileService;1"]
                               .getService(Ci.koIFileService)
            fname = tmpFileSvc.makeTempName(".html")
        }

        try {
            schemeService.convertToHTMLFile(view.scimoz,
                                            view.koDoc.displayPath,
                                            view.koDoc.language,
                                            lang.styleBits,
                                            view.koDoc.encoding.python_encoding_name,
                                            fname,
                                            selectionOnly,
                                            forceColor);
        } catch (e) {
            var lastErrorSvc = Cc["@activestate.com/koLastErrorService;1"]
                                 .getService(Ci.koILastErrorService);
            var errno = lastErrorSvc.getLastErrorCode();
            var errmsg = lastErrorSvc.getLastErrorMessage();
            ko.dialogs.alert("There was an error creating the HTML file '" + fname + "'",
                         errmsg);
            return false;
        }
        var URI = ko.uriparse.localPathToURI(fname);
        if (tofile) {
            ko.open.URI(URI);
        } else {
            var browser = null;
            if (preview) {
              browser = document.getElementById("printSource");
              log.debug("Setting up load listener...");
              _gBrowserLoadListener = (evt) =>
                window.setTimeout(exports.browserPrintPreview, 0, evt);
            } else {
              browser = document.getElementById("printBrowser");
              _gBrowserLoadListener = (evt) =>
                window.setTimeout(exports.browserPrint, 0, evt);
            }
            browser.addEventListener("load", _gBrowserLoadListener , true);
            browser.loadURI(URI, null);
            return true;
        }
    } catch (e) {
        log.exception(e);
    }
    return false;
}

exports.showPageSetup = function() {
    PrintUtils.showPageSetup();
};

var printBrowserListener = {
  print: null,
  get docSvc() {
        return Cc['@activestate.com/koDocumentService;1']
                 .getService(Ci.koIDocumentService);
  },
  QueryInterface : XPCOMUtils.generateQI([Ci.nsIWebProgressListener,
                                          Ci.nsISupportsWeakReference]),
  init : function() {},
  destroy : function() {},
  onStateChange : function(aWebProgress, aRequest, aStateFlags, aStatus) {
    if (aStateFlags & Ci.nsIWebProgressListener.STATE_STOP) {
        if (this.print) this.print();
    }
  },
  onProgressChange : function(aWebProgress, aRequest, aCurSelfProgress, aMaxSelfProgress, aCurTotalProgress, aMaxTotalProgress) {},
  onLocationChange : function(aWebProgress, aRequest, aLocation) {},
  onStatusChange : function(aWebProgress, aRequest, aStatus, aMessage) {},
  onSecurityChange : function(aWebProgress, aRequest, aState) {}
};

