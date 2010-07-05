/* Copyright (c) 2000-2010 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

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

    // Fill in Komodo License information.
    var licenseInfoWidget = iframe.document.getElementById("licenseinfo");
    licenseInfoWidget.appendChild(iframe.document.createTextNode(infoSvc.licenseInfo));

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
    clipboardHelper.copyString(_getBuildInfo()); 
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

