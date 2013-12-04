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

/**
 * Printing APIs -- stolen and adapted from mailWindowOverlay.js
 *
 */
const {Cc, Ci, Cu, Cr} = require("chrome");

var _gBrowserLoadListener = null;

const log = require("ko/logging").getLogger("printing");
const PrintUtils = window.PrintUtils;
Cu.import("resource://gre/modules/XPCOMUtils.jsm");

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

