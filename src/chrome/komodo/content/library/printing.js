/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

if (typeof(ko)=='undefined') {
    var ko = {};
}

/*
 * Printing APIs -- stolen and adapted from mailWindowOverlay.js
 *
 */
ko.printing = {};
(function() {
var _gBrowserLoadListener = null;
function getBrowser()
{
  return document.getElementById("printBrowser");
}

this.printPreview = function(view, preview, tofile, selectionOnly)
{
    window.openDialog("chrome://komodo/content/printPreview.xul",
                      "Komodo:PrintPreview",
                      "chrome,all,centerscreen",
                      view, preview, tofile, selectionOnly
                      );
}

this.browserPrintPreviewEnter = function() {
    document.getElementById("printPreviewDeck").setAttribute("selectedIndex",1);
    window.sizeToContent();
}

this.browserPrintPreviewExit = function() {
    window.close();
}

this.browserPrintPreview = function()
{
    try {
        var browser = document.getElementById("printBrowser");
        browser.removeEventListener("load", _gBrowserLoadListener, true);
        PrintUtils.printPreview(ko.printing.browserPrintPreviewEnter, ko.printing.browserPrintPreviewExit);
    } catch(e) { log.exception(e); }
}

this.browserPrint = function()
{
    try {
        var browser = document.getElementById("printBrowser");
        browser.removeEventListener("load", _gBrowserLoadListener, true);
        PrintUtils.print();
    } catch(e) { log.exception(e); }
}

this.print = function(view, preview, tofile, selectionOnly)
{
    try {
        var lang = view.document.languageObj;
        var schemeService = Components.classes['@activestate.com/koScintillaSchemeService;1'].getService()
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
            var newname = view.document.displayPath;
            var os = Components.classes['@activestate.com/koOs;1'].getService();
            if (view.document.isUntitled) {
                newname = os.path.realpath(os.path.join('.', newname));
            }
            newname = newname + '.html';
            var fname = ko.filepicker.saveFile(
                        os.path.dirname(newname), /* default directory */
                        newname, /* default name - knows about dirs */
                        "Save '"+os.path.basename(newname)+"' As...", "HTML");
            if (!fname) return false;
        } else {
            var tmpFileSvc = Components.classes["@activestate.com/koFileService;1"]
                             .getService(Components.interfaces.koIFileService)
            fname = tmpFileSvc.makeTempName(".html")
        }

        try {
            schemeService.convertToHTMLFile(view.scimoz,
                                            view.document.displayPath,
                                            view.document.language,
                                            lang.styleBits,
                                            view.document.encoding.python_encoding_name,
                                            fname,
                                            selectionOnly,
                                            forceColor);
        } catch (e) {
            var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
                               getService(Components.interfaces.koILastErrorService);
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
            var browser = document.getElementById("printBrowser");
            if (preview) {
              _gBrowserLoadListener = function(evt) { setTimeout(ko.printing.browserPrintPreview, 0, evt); };
            } else {
              _gBrowserLoadListener = function(evt) { setTimeout(ko.printing.browserPrint, 0, evt); };
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

var printBrowserListener = {
  print: null,
  get docSvc() {
        return Components.classes['@activestate.com/koDocumentService;1']
                .getService(Components.interfaces.koIDocumentService);
  },
  QueryInterface : function(aIID)
  {
    if (aIID.equals(Components.interfaces.nsIWebProgressListener) ||
        aIID.equals(Components.interfaces.nsISupportsWeakReference) ||
        aIID.equals(Components.interfaces.nsISupports))
    {
      return this;
    }
    throw Components.results.NS_NOINTERFACE;
  },
  init : function() {},
  destroy : function() {},
  onStateChange : function(aWebProgress, aRequest, aStateFlags, aStatus) {
    if (aStateFlags & Components.interfaces.nsIWebProgressListener.STATE_STOP) {
        if (this.print) this.print();
    }
  },
  onProgressChange : function(aWebProgress, aRequest, aCurSelfProgress, aMaxSelfProgress, aCurTotalProgress, aMaxTotalProgress) {},
  onLocationChange : function(aWebProgress, aRequest, aLocation) {},
  onStatusChange : function(aWebProgress, aRequest, aStatus, aMessage) {},
  onSecurityChange : function(aWebProgress, aRequest, aState) {}
};

}).apply(ko.printing);
