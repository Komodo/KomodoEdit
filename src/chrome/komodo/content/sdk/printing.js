/**
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState
 */

/**
 * The printing SDK allows you to access Komodo's printing facilities
 *
 * @module ko/printing
 */

/**
 * Printing APIs -- stolen and adapted from mailWindowOverlay.js
 *
 */
const {Cc, Ci, Cu, Cr} = require("chrome");

var _gBrowserLoadListener = null;

const log = require("ko/logging").getLogger("printing");
Cu.import("resource://gre/modules/XPCOMUtils.jsm");

// Get window/KO
var _window;
var legacy; // alias for ko
var _contextWindow;
var _PrintUtils;
try
{
    _window = require("ko/windows").getMain();
    _contextWindow = _window;
    legacy = _window.ko;
    _document = _window.document;
    _PrintUtils = _window.PrintUtils;
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

function _initPrintSettings() {
    if (!_PrintUtils._gOrigGetPrintSettings) {
        // Replace the _PrintUtils method with our own function, one that
        // customizes the print settings according to the users preference.
        _PrintUtils._gOrigGetPrintSettings = _PrintUtils.getPrintSettings;
        _PrintUtils.getPrintSettings = function() {
            /** @type {Components.interfaces.nsIPrintSettings} */
            var settings = _PrintUtils._gOrigGetPrintSettings();
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
        };
    }
}

/**
 * Set a contextual window for any further commands with this module.
 * If no window is passed in then the main window is used.
 */
exports.initWithWindow = (w) =>
{
    if( ! w)
    {
        _contextWindow = _window;
    }
    else
    {
        _contextWindow = w;
    }
    legacy = _contextWindow.ko;
    _document = _contextWindow.document;
    _PrintUtils = _contextWindow.PrintUtils;
};

/**
 * Open a print preview of the current file or selection
 *
 * @param   {Object}    view            Editor view
 * @param   {Boolean}   preview         Whether to preview the print
 * @param   {Boolean}   tofile          Print to a file
 * @param   {Boolean}   selectionOnly   Only print the selection
 */
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
        var browser = _document.getElementById("printSource");
        browser.removeEventListener("load", _gBrowserLoadListener, true);
        _PrintUtils.printPreview({
            getPrintPreviewBrowser: () => { return _document.getElementById("printBrowser"); },
            getSourceBrowser: () => { return browser; },
            getNavToolbox: () => { return _document.getElementById("printPreviewDeck"); },
            onEnter: () => {
                _document.getElementById("printPreviewDeck").setAttribute("selectedIndex",1);
                _contextWindow.sizeToContent();
                _contextWindow.setTimeout(()=>{_contextWindow.focus();},500);
            },
            onExit: () => { _contextWindow.close(); },
        });
    } catch(e) { log.exception(e); }
}

exports.browserPrint = function()
{
    try {
        var browser = _document.getElementById("printBrowser");
        browser.removeEventListener("load", _gBrowserLoadListener, true);
        _PrintUtils.print();
    } catch(e) { log.exception(e); }
}

/**
 * Print the given view (editor)
 *
 * @param   {Object}    view            Editor view
 * @param   {Boolean}   preview         Whether to preview the print
 * @param   {Boolean}   tofile          Print to a file
 * @param   {Boolean}   selectionOnly   Only print the selection
 */
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
            var fname = legacy.filepicker.saveFile(
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
            legacy.dialogs.alert("There was an error creating the HTML file '" + fname + "'",
                         errmsg);
            return false;
        }
        var URI = legacy.uriparse.localPathToURI(fname);
        if (tofile) {
            legacy.open.URI(URI);
        } else {
            var browser = null;
            if (preview) {
              browser = _document.getElementById("printSource");
              log.debug("Setting up load listener...");
              _gBrowserLoadListener = (evt) =>
                window.setTimeout(exports.browserPrintPreview, 0, evt);
            } else {
              browser = _document.getElementById("printBrowser");
              _gBrowserLoadListener = (evt) =>
                _contextWindow.setTimeout(exports.browserPrint, 0, evt);
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

/**
 * Open the print configuration dialog
 */
exports.showPageSetup = function() {
    _PrintUtils.showPageSetup();
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
