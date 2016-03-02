var { classes: Cc, interfaces: Ci, utils: Cu } = Components;
if (typeof(JetPack) === "undefined") {
    Cc["@mozilla.org/moz/jssubscript-loader;1"]
      .getService(Ci.mozIJSSubScriptLoader)
      .loadSubScript("chrome://komodo/content/jetpack.js", this);
}
var log = require("ko/logging").getLogger("startupWizard");
log.warn("CGCH!!!  It's working.");
var $ = require("ko/dom");

//console.log("CAREY DID IT!!!");
var elems =
{
    wizard : $("#startup-wizard"),
}

// Save all pref settings to be applied when the Finish button is pressed at the
// end of the wizard.  I don't want to half set prefs then have the user cancel
var prefSets = {};

function onLoad()
{
    // Start adding pages
    // Have to grab the ko/dom object from the Textbox to pass to addPage
    var textBox = require("ko/ui/textbox").create(
    { 
        attributes:
        {
            width: 100,
            focused: true,
            label: "This be a text box",
            value: "Enter something..."
        }
    });
    
    var page1 = require("ko/wizard/page").create(textBox.$elem,{ 
        attributes:
        {
            id: "page1",
            title: "Preferences",
            description: "Configure stuff here."
        }
    })
    
    
    
    //*
    // Here i'll just add page after page.  This will be long and ugly but the
    // easiest for now.
    
    // attach the final wizard to the window
    elems.wizard.append(page1.$elem);
    
}


/**
 * Apply all the prefs that we've gone through in the wizard to finalize the
 * process
 */
function finished()
{
    
}

function ok()
{
    var wizardComplete = new Event('wizard.complete');
    window.dispatchEvent(wizardComplete);
    log.warn("CGCH!!!  OK.");
    return;
}

function cancel()
{
    var wizardComplete = new Event('wizard.complete');
    window.dispatchEvent(wizardComplete);
   log.warn("CGCH!!! cancel");
    return true;
}

