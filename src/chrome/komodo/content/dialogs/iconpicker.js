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

/* A dialog to let the user pick an icon, either from a standard set of
   PNG files which Komodo ships with, or from a file the user has on
   his/her filesystem.

   The object returned has up to two properties:
    - retval: if "OK", then icon was picked.
    - value: if retval is "OK", then the URL of the selected file.
 */
var bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
        .getService(Components.interfaces.nsIStringBundleService)
        .createBundle("chrome://komodo/locale/dialogs/iconpicker.properties");
        
var log = ko.logging.getLogger("dialogs.iconpicker");
//log.setLevel(ko.logging.LOG_DEBUG);

var obj;
var gCurrentURI;
var files;
var os = Components.classes["@activestate.com/koOs;1"].getService();

var gIframe, gImgList, gWordList, gWordIndex, gIconFilter;

function OnLoad()
{
    try {
        obj = window.arguments[0];
        var dialog = document.getElementById("dialog-iconpicker");
        var okButton = dialog.getButton("accept");
        okButton.setAttribute("accesskey", bundle.GetStringFromName("okButton.accessKey"));
        var customButton = dialog.getButton("extra1");
        customButton.setAttribute("label", bundle.GetStringFromName("chooseOther"));
        var menulist = document.getElementById("icon-families");
        var lastSelectedIndex = parseInt(menulist.getAttribute("lastSelectedIndex"));
        menulist.selectedIndex = lastSelectedIndex;
        gIconFilter = document.getElementById("iconFilter");
        document.getElementById('iframe').
            addEventListener('load',
                             function() {
                                 if (gIconFilter.value) {
                                     doUpdateFilter(gIconFilter.value);
                                     gIconFilter.select();
                                 }
                             }, true); // bubbling events aren't fired
        selectIconFamily();
    } catch (e) {
        log.exception(e);
    }
}

function ValidatedPickIcon(uri)
{
    try {
        Pick_Icon(uri);
        OK();
        window.close();
    } catch (e) {
        log.exception(e);
    }
}

function Pick_Icon(uri) {
    try {
        gCurrentURI = uri;
        document.getElementById('icon32').setAttribute('src', uri + "?size=32");
        document.getElementById('icon16').setAttribute('src', uri);
        var os_path = Components.classes["@activestate.com/koOsPath;1"].getService();
        document.getElementById('iconlabel').setAttribute('value', os_path.withoutExtension(ko.uriparse.baseName(uri)));
    } catch (e) {
        log.exception(e);
    }
}

function selectIconFamily(event) {
    var selected = document.getElementById('icon-families').selectedItem;
    document.getElementById('iframe').setAttribute('src', selected.getAttribute('src'));
    gIframe = gImgList = null;
    // The iframe load eventListener will update filtering,
    // so there's nothing else to do here.
}

/**
 * Work around the iframe not showing the HTML img "title" tooltip, manually
 * creates and shows a tooltip for the HTML element when it has the "title"
 * attribute set.
 */
function FillInHTMLTooltip(tipElement) {
    // This FillInHTMLTooltip code comes from Mozilla forum:
    //   http://forums.mozillazine.org/viewtopic.php?f=19&t=561451
    var retVal = false;
    if (tipElement.namespaceURI == "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul") {
        return retVal;
    }
    const XLinkNS = "http://www.w3.org/1999/xlink";
    var titleText = null;
    var XLinkTitleText = null;
    while (!titleText && !XLinkTitleText && tipElement) {
        if (tipElement.nodeType == Node.ELEMENT_NODE) {
            titleText = tipElement.getAttribute("title");
            if (!titleText) {
                // Try the alt attribute then.
                titleText = tipElement.getAttribute("alt");
                if (!titleText) {
                    // Try the basename of the src attribute then.
                    titleText = tipElement.getAttribute("src");
                    if (titleText) {
                        titleText = titleText.split("/");
                        titleText = titleText[titleText.length - 1];
                    }
                }
            }
            XLinkTitleText = tipElement.getAttributeNS(XLinkNS, "title");
        }
        tipElement = tipElement.parentNode;
    }
    var texts = [titleText, XLinkTitleText];
    var tipNode = document.getElementById("aHTMLTooltip");
    for (var i = 0; i < texts.length; ++i) {
        var t = texts[i];
        if (t && t.search(/\S/) >= 0) {
            tipNode.setAttribute("label", t.replace(/\s+/g, " "));
            retVal = true;
        }
    }
    return retVal;
}

function OK()
{
    obj.value = gCurrentURI;
    obj.retval = "OK";
    var menulist = document.getElementById("icon-families");
    menulist.setAttribute("lastSelectedIndex", menulist.selectedIndex);
    return true;
}

function PickCustom()
{
    var prefName = "iconPicker.PickCustom";
    var default_dir = ko.filepicker.internDefaultDir(prefName);
    var path = ko.filepicker.browseForFile(default_dir, null, bundle.GetStringFromName("Select an Icon File"),
                                   'Icon', ['Icon', 'All']);
    if (!path) return;
    ko.filepicker.updateDefaultDirFromPath(prefName, path);
    Pick_Icon(ko.uriparse.localPathToURI(path));
}

function Cancel()
{
    obj.retval = "Cancel";
    return true;
}

var getLastPart_RE = /([^/]+?)(?:\.[^\.\/]+)?$/;
function doUpdateFilter(s) {
    if (!gIframe) {
        // Just index the current list of words. We can index each
        // set of words for each iframe if it comes to that, but I
        // assume most people will stick with one set of icons for
        // consistency.
        gIframe = document.getElementById("iframe");
        gImgList = Array.slice(gIframe.contentDocument.getElementsByTagName("img"));
        gWordList = [];
        gWordIndex = {};
        var lim = gImgList.length;
        for (var i = 0; i < lim; i++) {
            var word = gImgList[i].getAttribute('src').match(getLastPart_RE)[1];
            gWordList.push(word);
            gWordIndex[word] = i;
        }
    }
    if (!s) {
        gImgList.forEach(function(elt) elt.classList.remove("hide"));
        return;
    }
    // Mark everything to hide and then reveal only the hits.
    gImgList.forEach(function(elt) elt.classList.add("hide"));
    s = s.toLowerCase();
    var matchedWords = gWordList.filter(function(word) word.indexOf(s) >= 0);
    matchedWords.forEach(function(hitWord) {
            gImgList[gWordIndex[hitWord]].classList.remove("hide");
        });
}
