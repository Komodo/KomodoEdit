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

/* Dialog to select dirs in which to search for "Find in Files."
 *
 * Usage:
 *  All dialog interaction is done via an object passed in and out as the first
 *  window argument: window.arguments[0].
 *      .encodedFolders is a pathsep-separated list of selected diretories
 *      .cwd     is a directory in which to start browsing
 *  On return window.arguments[0] has:
 *      .retval         "OK" or "Cancel"
 *      .encodedFolders (only iff .retval=="OK") a list of the selected dirs
 *
 */

var log = ko.logging.getLogger("browseForDirs");
//log.setLevel(ko.logging.LOG_DEBUG);

var gAvailableDirsView = null;
var gSelectedDirsView = null;
var gWidgets = null;  // easy access to document elements


function OnLoad()
{
    try {
        gWidgets = new Object();
        var dialog = document.getElementById("dialog-browse-for-dirs")
        gWidgets.pathlist = document.getElementById("pathlist");
        gWidgets.okButton = dialog.getButton("accept");
        gWidgets.cancelButton = dialog.getButton("cancel");

        gWidgets.okButton.setAttribute("accesskey", "O");
        gWidgets.cancelButton.setAttribute("accesskey", "C");

        // .encodedFolders
        var encodedFolders = window.arguments[0].encodedFolders;
        if (typeof(encodedFolders) == "undefined") encodedFolders = null;
        if (encodedFolders) {
            gWidgets.pathlist.setData(encodedFolders);
        }
        if (window.arguments[0].cwd) {
            gWidgets.pathlist.setCwd(window.arguments[0].cwd);
        }
        gWidgets.pathlist.init();
    } catch(ex) {
        log.exception(ex);
    }
}


function OnUnload()
{
}


function OK()
{
    log.debug("OK()");
    try {
        window.arguments[0].retval = "OK";
        window.arguments[0].encodedFolders = gWidgets.pathlist.getData();
    } catch(ex) {
        log.exception(ex);
    }
    return true;
}

function Cancel()
{
    log.debug("Cancel()");
    try {
        window.arguments[0].retval = "Cancel";
    } catch(ex) {
        log.exception(ex);
    }
    return true;
}


