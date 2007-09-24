/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/* Komodo's Help->About dialog */

var log = ko.logging.getLogger("about");

//---- interface routines for XUL

function OnLoad()
{
    var infoSvc = Components.classes["@activestate.com/koInfoService;1"].
                  getService(Components.interfaces.koIInfoService);

    // Fill in Komodo build information.
    var buildInfoWidget = document.getElementById("build-info");
    var buildInfo = "Komodo " + infoSvc.prettyProductType +
                    ", version " + infoSvc.version +
                    ", build " + infoSvc.buildNumber +
                    ", platform " + infoSvc.buildPlatform +
                    ".\nBuilt on " + infoSvc.buildASCTime + ".";
    buildInfoWidget.value = buildInfo;

    // Give the Ok button the focus, otherwise the textbox might eat <Enter>.
    var dialog = document.getElementById("dialog-about");
    var okButton = dialog.getButton("accept");
    okButton.setAttribute("accesskey", "o");
    okButton.focus();

    window.sizeToContent();
    dialog.moveToAlertPosition();
}

