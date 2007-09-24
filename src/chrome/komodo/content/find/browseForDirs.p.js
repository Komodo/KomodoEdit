/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/* Dialog to select dirs in which to search for "Find in Files."
 *
 * Usage:
 *  All dialog interaction is done via an object passed in and out as the first
 *  window argument: window.arguments[0].
 *      .encodedFolders is a pathsep-separated list of selected diretories
 *      .currentDir     is a directory in which to start browsing (XXX:TODO)
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
        // .currentDir
        var currentDir = window.arguments[0].currentDir;
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


