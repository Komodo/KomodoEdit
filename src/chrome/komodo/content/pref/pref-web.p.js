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

const XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";

var gBrowsers, gBrowserTypes;
var gBrowserMenulist;

function PrefWeb_OnLoad()
{
    var prefbrowser = parent.hPrefWindow.prefset.getString('browser', '');

    // Get the list of available browsers.
    var koWebbrowser = Components.classes['@activestate.com/koWebbrowser;1'].
                   getService(Components.interfaces.koIWebbrowser);
    var browsersObj = {};
    var browserTypesObj = {};
    koWebbrowser.get_possible_browsers_and_types(
            {} /* count */, browsersObj, browserTypesObj);
    var gBrowsers = browsersObj.value;
    var gBrowserTypes = browserTypesObj.value;

    gBrowserMenulist = document.getElementById('selectedbrowser');
// #if PLATFORM == "win"
    gBrowserMenulist.appendItem('System defined default browser','');
// #else
    gBrowserMenulist.appendItem('Ask when browser is launched the next time', '');
// #endif

    var found = false;
    for (var i=0; i < gBrowsers.length; i++) {
        _addBrowser(gBrowsers[i], gBrowserTypes[i]);
        if (gBrowsers[i] == prefbrowser) found = true;
    }
    if (!found && prefbrowser) {
        _addBrowser(prefbrowser, null);
    }

    parent.hPrefWindow.onpageload();
}


/* Add the given browser to the browser menulist and return the added item. */
function _addBrowser(browser, browserType /* =null */) {
    if (typeof(browserType) == "undefined") browserType = null;

    var popup = document.getElementById("selectedbrowser-popup");
    var item = document.createElementNS(XUL_NS, "menuitem");
    item.setAttribute("label", browser);
    item.setAttribute("value", browser);
    item.setAttribute("crop", "center");
    if (browserType) {
        //TODO: This styling doesn't work here and I don't know why.
        //      The equivalent works for the "browser preview" toolbar
        //      button in komodo.xul.
        item.setAttribute("class", "menuitem-iconic browser-"+browserType+"-icon");
    }
    popup.appendChild(item);
    return item;
}

function browseForBrowser() {
    var prefName = "prefWeb.browseForBrowser";
    var gBrowserMenulist = document.getElementById("selectedbrowser");
    var default_dir = (getDirectoryFromTextObject(gBrowserMenulist)
                       || ko.filepicker.internDefaultDir(prefName));
    var path = ko.filepicker.browseForExeFile(default_dir);
    if (path == null) {
        return null;
    }
    ko.filepicker.updateDefaultDirFromPath(prefName, path);
    path = path.replace('"', '\\"', 'g');
    if (path.indexOf(' ') != -1) {
        path = '\"' + path + '\"';
    }
    gBrowserMenulist.selectedItem = _addBrowser(path);
    return null;
}


function configureProxies() {
    ko.windowManager.openDialog(
        "chrome://komodo/content/pref/pref-proxies.xul",
        "Komodo:ProxyPrefs",
        "chrome,modal,resizable,close,centerscreen",
        null);
}

function showCertificates() {
    ko.windowManager.openDialog(
        "chrome://pippki/content/certManager.xul",
        "mozilla:certmanager",
        "chrome,modal,resizable,close,centerscreen",
        null);
}
