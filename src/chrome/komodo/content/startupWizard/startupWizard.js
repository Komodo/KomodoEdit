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
var canFinish = true; // Used to know if the entries are all valid.

var elems =
{
    wizard : $("#startup-wizard"),
}



// Save all pref settings to be applied when the Finish button is pressed at the
// end of the wizard.  I don't want to half set prefs then have the user cancel
var storedPrefs = {};

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
    var keybindingMenulist = require("ko/ui/menulist").create({
        attributes:
        {
            label:"Keybinding sets",
            width: 100,
            
        }
    });
    var prefname = "keybinding_scheme";
    for (let i in allKeybindingConfigs)
    {
        keybindingMenulist.addMenuitem({
            attributes: {
                label: allKeybindingConfigs[i],
                oncommand: "return storePref([\"" + prefname + "\", \"" + allKeybindingConfigs[i] + "\"]);",
                tooltiptext: "See Preferences > Keybindings for more details"
            }
        });
    }
    page1.addRow(keybindingMenulist.$elem);
    
    // Add toggles:
    // Native window borders,
    // minimap scroll
    // use tabs over spaces
    // enable word wrap
    // wrap selections
    // auto-abbreviations
    // tab completions
    var nativeWindowPrefs = ! prefs.getBoolean("ui.hide.chrome");
    storePref(["ui_hide_chrome", nativeWindowPrefs]);
    var minimapPref = prefs.getBoolean("editShowMinimap");
    storePref(["editShowMinimap", minimapPref])
    var useTabsPref = prefs.getBoolean("useTabs");
    storePref(["useTabs", useTabsPref]);
    var useWordwrap = prefs.getLong("editWrapType");
    storePref(["editWrapType", useWordwrap]);
    var wrapSelectPref = prefs.getBoolean("editSmartWrapSelection");
    storePref(["editSmartWrapSelection", wrapSelectPref]);
    var enableAutoSnippetsPref = prefs.getBoolean("enableAutoAbbreviations");
    storePref(["enableAutoAbbreviations", enableAutoSnippetsPref]);
    var enableTabComplete = prefs.getBoolean("editTabCompletes");
    storePref(["editTabCompletes", enableTabComplete]);
    
    // word wrap can have 3 states.  No need to over complicate the
    // UI so if they already have wordwrap set, keep it that on
    // with the setting they had, eg. wrap on word or char (1 or 2)
    // Assume 1 (wrap on word) if it was never set and user wants
    // it set now.
    var setWordWrapPref = function(){
        if(this.checked) 
            {
                if(useWordwrap == 0)
                storePref(["useTabs", useWordwrap]);
            }
            else if (this.checked)
            {
                storePref(["useTabs", 1]);
            }
            else
            {
                storePref(["useTabs", 0]);
            }
    }
    
    var checkboxes =
    [
        {
            // Enable Native windows
            attributes: {
                checked: nativeWindowPrefs,
                label: "Enable native window borders.",
                oncommand:  "return storePref([\"ui_hide_chrome\", !this.checked])",
            }
        },
        {
            // Enable minimap
            attributes: {
                checked: minimapPref,
                label: "Enable Minimap scrolling.",
                oncommand: "return storePref([\"editShowMinimap\", this.checked])",
            }
        },
        {
            // prefer tabs over spaces
            attributes: {
                checked: useTabsPref,
                label: "Prefer tab characters over spaces.",
                oncommand: "return storePref([\"useTabs\", this.checked])",
            }
        },
        {
            // Enable word wrap
            attributes: {
                checked: useWordwrap == 0 ? false : true,
                label: "Enable line wrapping on words.",
                oncommand: "return setWordWrapPref();"
            }
        },
        {
            // Wrap selections
            attributes: {
                checked: wrapSelectPref,
                tooltiptext: "See Prefereces > Editor > Smart editing for more details",
                label: "Wrap selection with typed delimiter",
                oncommand: "return storePref([\"editSmartWrapSelection\", this.checked]);"
            }
        },
        {
            // Auto Snippets 
            attributes: {
                checked: enableAutoSnippetsPref,
                tooltiptext: "See Prefereces > Editor > Smart editing: Auto-Abbreviations for more details",
                label: "Enable auto snippets to trigger while typing.",
                oncommand: "return storePref([\"enableAutoAbbreviations\", this.checked]);"
            }
        },
        {
            attributes: {
                checked: enableTabComplete,
                tooltiptext: "See Prefereces > Editor > Smart editing for more details",
                label: "Enable Tab key word completion.",
                oncommand: "return storePref([\"editTabCompletes\", this.checked]);"
            }
        }
    ]
    
    
    for(let i in checkboxes)
    {
        var checkbox = require("ko/ui/checkbox").
            create({ //options
                attributes: checkboxes[i].attributes
            });
        page1.addRow(checkbox.$elem);
    }
    //// End adding checkboxes toggles
    
    // Add browser preview choice
    var browserMenulist = require("ko/ui/menulist").create({
        attributes:
        {
            label:"Browser Preview Browser",
            width: 200,
            
        }
    });
    var koWebbrowser = Components.classes['@activestate.com/koWebbrowser;1'].
                   getService(Components.interfaces.koIWebbrowser);
    var knownBrowsers = koWebbrowser.get_possible_browsers({});
    for (let i in knownBrowsers)
    {
        browserMenulist.addMenuitem({
            attributes: {
                label: knownBrowsers[i],
                oncommand: "return storePref(['browser', \"" + knownBrowsers[i] + "\"]);",
                tooltiptext:  knownBrowsers[i]
            }
        });
    }
    page1.addRow(browserMenulist.$elem);
    
    
    // Add set tab width pref
    var tabWidth = prefs.getLong("tabWidth")
    var textboxAttrs =
    {
        label: "Set global with of tabs and indents in spaces.",
        value: tabWidth,
        width: 20,
        tooltiptext: "tab/indent width in spaces",
        onkeyup: function(){
            log.error("the field is: " + this.value);
        }
    }
    var tabWidthTextfield = require("ko/ui/textbox").create(
        {attributes: textboxAttrs}
    )
    page1.addRow(tabWidthTextfield.$elem);
    // Done adding tab width prefs
    
    
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

