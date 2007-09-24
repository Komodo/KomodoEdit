/* Copyright (c) 2003-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

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

