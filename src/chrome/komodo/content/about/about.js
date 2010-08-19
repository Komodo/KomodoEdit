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
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2010
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

/* Komodo's About dialog */

var log = ko.logging.getLogger("about");
var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
        .getService(Components.interfaces.nsIStringBundleService)
        .createBundle("chrome://komodo/locale/about.properties");
var infoSvc = Components.classes["@activestate.com/koInfoService;1"].
              getService(Components.interfaces.koIInfoService);


//---- interface routines for XUL

function onLoad()
{
    var iframe = window.frames[0];

    // Fill in Komodo build information.
    var buildInfoWidget = iframe.document.getElementById("buildinfo");
    var buildInfo = _getBuildInfo();
    // Note: Would be nice to translate '\n' to <br> or put in a styled textarea.
    buildInfoWidget.appendChild(iframe.document.createTextNode(buildInfo));

    window.getAttention();
}


function copyBuildInfo(event) {
    const clipboardHelper = Components.classes["@mozilla.org/widget/clipboardhelper;1"].  
        getService(Components.interfaces.nsIClipboardHelper);  
    var iframe = window.frames[0];
    var selection = iframe.getSelection().toString();
    if (!selection) {
        selection = _getBuildInfo();
    }
    clipboardHelper.copyString(selection); 
}

function iframeOnClickHandler(event) {
    if (event.target.getAttribute('id') == 'copy_button') {
        copyBuildInfo();
    }
}

//---- internal support stuff

function _getBuildInfo() {
    var buildInfo = _bundle.formatStringFromName("aboutInfo.message",
            [infoSvc.prettyProductType,
             infoSvc.version,
             infoSvc.buildNumber,
             infoSvc.buildPlatform,
             infoSvc.buildASCTime], 5);
    var brandingPhrase = infoSvc.brandingPhrase;
    if (brandingPhrase) {
        buildInfo += "\n"+brandingPhrase;
    }
    return buildInfo;
}

