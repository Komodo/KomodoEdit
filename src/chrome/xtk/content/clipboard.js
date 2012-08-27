/*
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Initial Developer of the Original Code is
# Davide Ficano.
# Portions created by the Initial Developer are Copyright (C) 2008
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Davide Ficano <davide.ficano@gmail.com>
#   ActiveState Software Inc.
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****
*/

/*
 *
 * Functions for accessing to clipboard.
 *
 * Summary of Functions:
 *  xtk.clipboard.setText                Copy plain text to clipboard.
 *  xtk.clipboard.getText                Get plain text from clipboard.
 *  xtk.clipboard.getHtml                Get HTML source code from clipboard.
 *                                       Must be sure clipboard contains HTML
 *  xtk.clipboard.containsHtml           Check if clipboard contains HTML source
 *                                       code.
 *  xtk.clipboard.containsFlavors        Check if clipboard contains specific
 *                                       formats (ie flavors).
 *  xtk.clipboard.createTransferable     Create a transferable object useful
 *                                       to copy multiple formats to clipboard.
 *  xtk.clipboard.copyFromTransferable   Copy multiple format to clipboard.
 *
 */

 /*
  Example usage:

    var html = "<span style='color:red'>hello color</span>";
    var text = "hello normal";
    
    var transferable = xtk.clipboard.addTextDataFlavor("text/html", html);
    transferable = xtk.clipboard.addTextDataFlavor("text/unicode", text, transferable);
    xtk.clipboard.copyFromTransferable(transferable);
    
    v = "";
    if (xtk.clipboard.containsHtml()) {
        v = xtk.clipboard.getHtml();
    } else {
        v = "No HTML code found in clipboard";
    }
    
    alert("html\n" + v + "\n\nText\n" + xtk.clipboard.getText());
    
    xtk.clipboard.setText("new text in cb");
 */


if (typeof(xtk) == 'undefined') {
    var xtk = {};
}
if (typeof(xtk.clipboard) == 'undefined') {
    /**
     * Useful clipboard functions.
     */
    xtk.clipboard = {};
}

(function() {

const { classes: Cc, interfaces: Ci, utils: Cu } = Components;
Cu.import("resource://gre/modules/Services.jsm");

var _cbSvc = Components.classes["@mozilla.org/widget/clipboard;1"]
                .getService(Components.interfaces.nsIClipboard);
var flavorSupportsCStringMap = {};

this.emptyClipboard = function() {
    _cbSvc.emptyClipboard(_cbSvc.kGlobalClipboard);
}

this.getTextFlavor = function(textFlavor) {
    var transferable = this.createTransferable();
    if (_cbSvc && transferable) {
        transferable.addDataFlavor(textFlavor);

        _cbSvc.getData(transferable, _cbSvc.kGlobalClipboard);

        var str       = {};
        var strLength = {};
    
        transferable.getTransferData(textFlavor, str, strLength);
        if (str.value && str.value instanceof Ci.nsISupportsString) {
            // Gecko returns the number of bytes, instead of number of chars...
            return str.value.data.substr(0, strLength.value / 2);
        }
        if (str.value && str.value instanceof Ci.nsISupportsCString) {
            return str.value.data;
        }
    }
    return null;
}

/**
 * Get HTML source code from clipboard.
 * @returns {string}  The html text from the clipboard.
 */
this.getHtml = function() {
    if (this.containsFlavors(["text/html"])) {
        return this.getTextFlavor("text/html");
    }

    // No normal text/html, try native HTML on Windows.
    if (Services.appinfo.OS == "WINNT" &&
        this.containsFlavors(["application/x-moz-nativehtml"]))
    {
        let data = this.getTextFlavor("application/x-moz-nativehtml");
        // The HTML clipboard format is documented at
        // http://msdn.microsoft.com/en-us/library/ms649015.aspx
        // It has a header (lines ending with any of CR, CRLF, LF).
        // The start of the content is determined by the "StartHTML" header.
        let metadata = { StartHTML: Number.POSITIVE_INFINITY };
        let lineMatcher = new RegExp("\r\n|\r|\n", "mg");
        do {
            let startIndex = lineMatcher.lastIndex;
            if (!lineMatcher.exec(data)) {
                break;
            }
            let line = data.substring(startIndex, lineMatcher.lastIndex)
                           .replace(/[\r\n]+$/, "");
            let [, key, value] = /([^:]+):(.*)/.exec(line);
            if (/^(?:Start|End)(?:HTML|Fragment|Selection)$/.test(key)) {
                value = parseInt(value, 10); // This is a decimal number
            }
            metadata[key] = value;
        } while (lineMatcher.lastIndex < metadata.StartHTML);
        if (("StartFragment" in metadata) && ("EndFragment" in metadata)) {
            data = data.substring(metadata.StartFragment, metadata.EndFragment);
        } else if (("StartHTML" in metadata) && ("EndHTML" in metadata)) {
            data = data.substring(metadata.StartHTML, metadata.EndHTML);
        }
        return data;
    }

    // This will fail - and throw an appropriate exception
    return this.getTextFlavor("text/html");
}

/**
 * Get plain text from clipboard.
 * @returns {string}  The text from the clipboard.
 */
this.getText = function() {
    return this.getTextFlavor("text/unicode");
}

/**
 * Check if clipboard contains text in HTML format. Returns true if clipboard
 * contains HTML text, false otherwise.
 * @returns {boolean}
 */
this.containsHtml = function() {
    let flavours = ["text/html"];
    if (Services.appinfo.OS == "WINNT") {
        // Try the Windows native HTML format (CF_HTML).
        flavours.push("application/x-moz-nativehtml");
    }
    return this.containsFlavors(flavours);
}

/**
 * Check if clipboard contains at least one of passed formats (ie flavor).
 * Returns true if clipboard contains one of passed flavor, false otherwise.
 *
 * @param {array} flavors  Mime-type strings (eg ["text/html", "text/unicode"])
 * @returns {boolean}
 */
this.containsFlavors = function(flavors) {
    const kClipboardIID = Components.interfaces.nsIClipboard;

    if (kClipboardIID.number == "{8b5314ba-db01-11d2-96ce-0060b0fb9956}") {
        var flavorArray = Components.classes["@mozilla.org/supports-array;1"]
            .createInstance(Components.interfaces.nsISupportsArray);

        for (var i = 0; i < flavors.length; ++i) {
            var kSuppString = Components.classes["@mozilla.org/supports-cstring;1"]
                           .createInstance(Components.interfaces.nsISupportsCString);
            kSuppString.data = flavors[i];
            flavorArray.AppendElement(kSuppString);
        }        
        return _cbSvc.hasDataMatchingFlavors(flavorArray, _cbSvc.kGlobalClipboard);
    } else {
        return _cbSvc.hasDataMatchingFlavors(flavors, flavors.length,
                                             kClipboardIID.kGlobalClipboard);
    }
}

this._getSupportsCString = function(flavor) {
    var supportCString = flavorSupportsCStringMap[flavor];
    
    if (typeof (supportCString) == "undefined") {
        supportCString = Components.classes["@mozilla.org/supports-cstring;1"]
                       .createInstance(Components.interfaces.nsISupportsCString);
        supportCString.data = flavor;
        flavorSupportsCStringMap[flavor] = supportCString;
    }
    
    return supportCString;
}

/**
 * Create a transferable object useful to copy multiple formats to clipboard
 * and return with it.
 *
 * @returns {Components.interfaces.nsITransferable}
 */
this.createTransferable = function() {
    return Components.classes["@mozilla.org/widget/transferable;1"]
                    .createInstance(Components.interfaces.nsITransferable);
}

/**
 * Add a text flavor (eg html or plain text) to a transferable object, if
 * passed transferable is null or not defined a new one is created.
 * Returns the tranferable object.
 *
 * @param {string} flavor  The mime-type flavor (eg "text/html").
 * @param {string} text  The text to add.
 * @param transferable {Components.interfaces.nsITransferable}
 *        (Optional)  The tranferable to use, if null a new object is created.
 *
 * @returns {Components.interfaces.nsITransferable}
 */
this.addTextDataFlavor = function(flavor, text, transferable) {
    if (!transferable) {
        transferable = this.createTransferable();
    }
    transferable.addDataFlavor(flavor);
    var string = Components.classes["@mozilla.org/supports-string;1"]
                    .createInstance(Components.interfaces.nsISupportsString);
    string.data = text;
    transferable.setTransferData(flavor, string, text.length * 2);
    
    return transferable;
}

/**
 * Copy to clipboard using a tranferable object, this allows to copy text in
 * multiple format for example the same text as HTML and plain text.
 *
 * @param transferable {Components.interfaces.nsITransferable}
 *        The tranferable object
 */
this.copyFromTransferable = function(transferable) {
    if (!transferable) {
        return;
    }
    _cbSvc.setData(transferable, null,
                   Components.interfaces.nsIClipboard.kGlobalClipboard);
}

/**
 * Set the clipboard to contain the plain text provided.
 *
 * @param {string} text  The text to copy to clipboard.
 */
this.setText = function(text) {
    var transferable = this.addTextDataFlavor("text/unicode", text);
    xtk.clipboard.copyFromTransferable(transferable);
}

}).apply(xtk.clipboard);
