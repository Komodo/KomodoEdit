/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/. */

const koWindow  = window.opener;
const ko        = koWindow.ko;
const Services  = koWindow.Services;

const { classes: Cc, interfaces: Ci, utils: Cu } = koWindow.Components;

document.addEventListener('DOMContentLoaded', function()
{

    var links = document.querySelectorAll(".button-link[href]");
    
    for (let [,link] in Iterator(links))
    {
        link.addEventListener("click", function()
        {
            ko.browse.openUrlInDefaultBrowser(this.getAttribute("href"));
        }.bind(link));
    }

    var koMajorMinor = ko.version.split(".").slice(0, 2).join(".");
    var prefName = 'show-getstarted-' + koMajorMinor;
    var showGetStarted  = ko.prefs.getBoolean(prefName, false);
    var checkbox        = document.getElementById('showGetStartedCheck');
    if (showGetStarted)
    {
        checkbox.checked = true;
    }

    checkbox.addEventListener("click", function()
    {
        showGetStarted = ! showGetStarted;
        ko.prefs.setBoolean(prefName, showGetStarted);
    });

    // Close dialog when escape key is pressed
    document.addEventListener("keyup", function(e)
    {
        if (e.keyCode==27) // Escape key
        {
            window.close();
        }
    });

});

(function()
{
    function setWindowPosition()
    {
        // Execute at end of event loop so as not to interfere with default window centering
        setTimeout(function()
        {
            // Force the window to be centered, OSX doesn't handle centerscreen well
            window.screenX = ((koWindow.innerWidth - window.innerWidth)/2) + koWindow.screenX,
            window.screenY = ((koWindow.innerHeight - window.innerHeight)/2) + koWindow.screenY;
        });
    }

    window.addEventListener('load', setWindowPosition);

})();
