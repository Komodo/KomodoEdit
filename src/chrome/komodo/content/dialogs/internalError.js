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

/* A dialog to notify the user of an unexpected Komodo error and to encourage
 * them to report it.
 *
 * Usage:
 *  All dialog interaction is done via the following arguments passed in.  Two
 *  ways of passing in args are supported (to allow usage of both
 *  window.openDialog() and nsIWindowWatcher.openWindow() for this dialog).
 *  The first is as attributes of an object passed in as window.arguments[0].
 *  The second is as strings.
 *      window.arguments[0].error  or  window.arguments[0]
 *          A short description of the error.
 *      window.arguments[0].text  or  window.arguments[1]
 *          A string of text that will be displayed in a non-edittable
 *          selectable text box. Generally this is some text that the user is
 *          encouraged to quote in their bug report.
 */

var log = ko.logging.getLogger("dialogs.internalError");
//log.setLevel(ko.logging.LOG_DEBUG);



//---- interface routines for XUL

function OnLoad()
{
    try {
        var dialog = document.getElementById("dialog-internalerror");
        var okButton = dialog.getButton("accept");
        okButton.setAttribute("accesskey", "o");

        var error, text;
        if (typeof(window.arguments[0]) == "string") {
            error = window.arguments[0];
            text = window.arguments[1];
        } else {
            error = window.arguments[0].error;
            text = window.arguments[0].text;
        }

        // error
        var errorWidget = document.getElementById("error");
        var textUtils = Components.classes["@activestate.com/koTextUtils;1"]
                            .getService(Components.interfaces.koITextUtils);
        error = textUtils.break_up_words(error, 50);
        var textNode = document.createTextNode(error);
        errorWidget.appendChild(textNode);

        // text
        var textWidget = document.getElementById("text");
        var infoSvc = Components.classes["@activestate.com/koInfoService;1"].
                      getService(Components.interfaces.koIInfoService);
        var verInfo = "Komodo " + infoSvc.prettyProductType + ", version " +
                      infoSvc.version + ", build " + infoSvc.buildNumber +
                      ".\nBuilt on " + infoSvc.buildASCTime + ".";
        textWidget.removeAttribute("collapsed");
        textWidget.value = text + "\n\n" + verInfo;

        window.sizeToContent();
        if (!opener || opener.innerHeight == 0) { // indicator that opener hasn't loaded yet
            dialog.centerWindowOnScreen();
        } else {
            dialog.moveToAlertPosition(); // requires a loaded opener
        }
        // Otherwise the textbox is given focus and it eats <Enter>.
        okButton.focus();
    } catch(ex) {
        log.exception(ex, "Error loading 'Internal Error' dialog.");
    }
    window.getAttention();
}

function Browse(url)
{
    try {
        ko.browse.openUrlInDefaultBrowser(url);
    } catch(ex) {
        log.exception(ex, "Error trying to open '"+url+"' in default browser.");
    }
}

