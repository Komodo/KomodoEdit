var { classes: Cc, interfaces: Ci, utils: Cu } = Components;
if (typeof(JetPack) === "undefined") {
    Cc["@mozilla.org/moz/jssubscript-loader;1"]
      .getService(Ci.mozIJSSubScriptLoader)
      .loadSubScript("chrome://komodo/content/jetpack.js", this);
}
var log = require("ko/logging").getLogger("startupWizard");
log.setLevel(10);
var $ = require("ko/dom");
var prefs = require("ko/prefs");

var elems =
{
    wizard : $("#startup-wizard"),
}



// Save all pref settings to be applied when the Finish button is pressed at the
// end of the wizard.  I don't want to half set prefs then have the user cancel
var storedPrefs = {
    keybinding_scheme: "",
    
    };

function onLoad()
{
    // Start adding pages
    // Have to grab the ko/dom object from the Textbox to pass to addPage
        
    
    /**
     *  START PAGE ONE
     */
    var page1 = require("ko/wizard/page").create({ 
        attributes:
        {
            id: "page1",
            title: "Keybindings",
            description: "Pick a keybinding set you'll be most comfortable with using."
        }
    })
    
    // Populate the keybinding dropdown
    
    //This should set which item is selected by default when the list is generated
    var currentKeybindingConfig = prefs.getStringPref("keybinding-scheme");
    var schemes = new Array();
    var keybindingService =  Cc['@activestate.com/koKeybindingSchemeService;1'].getService();
    keybindingService.getSchemeNames(schemes, new Object());
    var allKeybindingConfigs = schemes.value;
    var menulist = require("ko/ui/menulist").create({
        attributes:
        {
            label:"Keybinding sets",
            width: 100,
            
        }
    });
    var menuitems = [];
    var prefname = "keybinding_scheme";
    for (var i in allKeybindingConfigs)
    {
        menulist.addMenuitem([
                    allKeybindingConfigs[i],
                    "return storePref([\"" + prefname + "\", \"" + allKeybindingConfigs[i] + "\"]);"
                ]);
    }
    page1.addRow(menulist.$elem);
    
    // Add toggles:
    // Native window borders,
    // minimap scroll 
    var nativeWindowPrefs = ! prefs.getBoolean("ui.hide.chrome")
    var minimapPref = prefs.getBoolean("editShowMinimap");
    var checkboxes =
    [
        {
            label: "Enable native window borders.",
            command:  function(){ // command for checkbox when toggled
                                    storePref(["ui_hide_chrome", !this.checked])
                                },
            attributes: {
                checked: nativeWindowPrefs
            }
        },
        {
            label: "Enable Minimap scrolling.",
            command: function(){ // command for checkbox when toggled
                                    storePref(["editShowMinimap", this.checked])
                                },
            attributes: {
                checked: minimapPref
            }
        }
        
    ]
    for(let i in checkboxes)
    {
         var checkbox = require("ko/ui/checkbox").
                                        create(checkboxes[i].label,
                                               checkboxes[i].command,
                                                { //options
                                                    attributes: checkboxes[i].attributes
                                                });
        page1.addRow(checkbox.$elem);
    }
    
    
    
    //*
    // Here I'll just add page after page.  This will be long and ugly but the
    // easiest for now.
    
    // attach the final wizard to the window
    elems.wizard.append(page1.$elem);
    /**
     *  END PAGE ONE
     */
}

/**
 * Store preferences choice by user
 *
 * @param {String[]} prefset  two item list of pref name and value
 */
function storePref(prefset)
{
    storedPrefs[prefset[0]] = prefset[1];
    log.debug("Storing pref: " + storedPrefs[prefset[0]]);
}

/**
 * Apply all the prefs that we've gone through in the wizard to finalize the
 * process
 */
function finished()
{
    // Apply pref settings saved in prefSet
    //below sets the native border pref
    //prefs.setBoolean("ui.hide.chrome",
    //                 ! this.elem.element().checked);
    prefs.setBoolean("wizard.finished", true);
    var wizardComplete = new Event('wizard.complete');
    window.dispatchEvent(wizardComplete);
    
    return true;
}

function ok()
{
    var wizardComplete = new Event('wizard.complete');
    window.dispatchEvent(wizardComplete);
    return;
}

function cancel()
{
 //    THIS MUST BE REMOVED!!!!
    prefs.setBoolean("wizard.finished", true);
    var wizardComplete = new Event('wizard.complete');
    window.dispatchEvent(wizardComplete);
    
    return true;
}

