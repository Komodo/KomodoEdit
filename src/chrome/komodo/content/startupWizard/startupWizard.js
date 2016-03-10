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
var storedPrefs = [];

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
            title: "Configure Komodo",
            description: "Configure Komodo with basic editing settings that best fit you're workflow."
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
            id: "keybinding-list",
            label:"Keybinding sets",
            width: 100,
            
        }
    });
    var prefname = "keybinding-scheme";
    for (let i in allKeybindingConfigs)
    {
        keybindingMenulist.addMenuitem({
            attributes: {
                label: allKeybindingConfigs[i],
                tooltiptext: "See Preferences > Keybindings for more details"
            }
        });
    }
     keybindingMenulist.$elem.on("command", function()
                             {
                                storePref(['keybinding-scheme',
                                           this.selectedItem.label, 'string']);
                                keybindingService.getScheme(this.selectedItem.label);
                             });
    page1.addRow(keybindingMenulist.$elem);
    
    // ADD TOGGLES:
    // Native window borders,
    // minimap scroll
    // use tabs over spaces
    // enable word wrap
    // wrap selections
    // auto-abbreviations
    // tab completions
    var nativeWindowPrefs = ! prefs.getBoolean("ui.hide.chrome");
    var minimapPref = prefs.getBoolean("editShowMinimap");
    var useTabsPref = prefs.getBoolean("useTabs");
    var useWordwrap = prefs.getLong("editWrapType");
    var wrapSelectPref = prefs.getBoolean("editSmartWrapSelection");
    var enableAutoSnippetsPref = prefs.getBoolean("enableAutoAbbreviations");
    var enableTabComplete = prefs.getBoolean("editTabCompletes");

    var checkboxes =
    [
        {
            // Enable Native windows
            attributes: {
                checked: nativeWindowPrefs,
                label: "Enable native window borders.",
                oncommand:  "return storePref([\"ui.hide.chrome\", !this.checked, \"bool\"])",
            }
        },
        {
            // Enable minimap
            attributes: {
                checked: minimapPref,
                label: "Enable Minimap scrolling.",
                oncommand: "return storePref([\"editShowMinimap\", this.checked, \"bool\"])",
            }
        },
        {
            // prefer tabs over spaces
            attributes: {
                checked: useTabsPref,
                label: "Prefer tab characters over spaces.",
                oncommand: "return storePref([\"useTabs\", this.checked, \"bool\"])",
            }
        },
        {
            // Enable word wrap
            attributes: {
                id: "wordwrap",
                checked: useWordwrap == 0 ? false : true,
                label: "Enable line wrapping on words.",
                tooltiptext: "See Prefereces > Editor > Smart editing for more details",
            }
        },
        {
            // Wrap selections
            attributes: {
                checked: wrapSelectPref,
                tooltiptext: "See Prefereces > Editor > Smart editing for more details",
                label: "Wrap selection with typed delimiter",
                oncommand: "return storePref([\"editSmartWrapSelection\", this.checked, \"bool\"]);"
            }
        },
        {
            // Auto Snippets 
            attributes: {
                checked: enableAutoSnippetsPref,
                tooltiptext: "See Prefereces > Editor > Smart editing: Auto-Abbreviations for more details",
                label: "Enable auto snippets to trigger while typing.",
                oncommand: "return storePref([\"enableAutoAbbreviations\", this.checked, \"bool\"]);"
            }
        },
        {
            attributes: {
                checked: enableTabComplete,
                tooltiptext: "See Prefereces > Editor > Smart editing for more details",
                label: "Enable Tab key word completion.",
                oncommand: "return storePref([\"editTabCompletes\", this.checked, \"bool\"]);"
            }
        }
    ]
    for(let i in checkboxes)
    {
        var checkbox = require("ko/ui/checkbox").
            create({ //options
                attributes: checkboxes[i].attributes
            });
        // Move checkbox command assignment here
        // checkbox.$elem.on("command", function(){...});
        page1.addRow(checkbox.$elem);
    }
    // word wrap can have 3 states.  No need to over complicate the
    // UI so if they already have wordwrap set, keep it that on
    // with the setting they had, eg. wrap on word or char (1 or 2)
    // Assume 1 (wrap on word) if it was never set and user wants
    // it set now.
    
    ///THIS NEVER GETS CALLED AND I DON"T KNOW WHY
    $('#wordwrap').on("command",/* [useWordwrap],*/ function(event)
                      {
                         //if(this.checked) 
                         //   {
                         //       if(data == 0)
                         //       storePref(["useTabs", event.data, "long"]);
                         //   }
                         //   else if (this.checked)
                         //   {
                         //       storePref(["useTabs", 1, "long"]);
                         //   }
                         //   else
                         //   {
                         //       storePref(["useTabs", 0, "long"]);
                         //   }
                         log.debug("Saving the word wrap pref");
                      });
    //// End ADD TOGGLES
    
    // Add browser preview choice
    var browserMenulist = require("ko/ui/menulist").create({
        attributes:
        {
            id: "browser-list",
            label:"Browser Preview Browser",
            width: 200,
            
        }
    });
    var koWebbrowser = Components.classes['@activestate.com/koWebbrowser;1'].
                   getService(Components.interfaces.koIWebbrowser);
    var knownBrowsers = koWebbrowser.get_possible_browsers({});
//// #if PLATFORM == "win"
//     browserMenulist.addMenuitem({
//                                 attributes: {
//                                    label: 'System defined default browser',
//                                 }
//     });
//// #else
//    browserMenulist.addMenuitem({
//                                 attributes: {
//                                    label: 'Ask when browser is launched the next time',
//                                 }
//     });
//// #endif
    
    for (let i in knownBrowsers)
    {
        browserMenulist.addMenuitem({
            attributes: {
                label: knownBrowsers[i],
                tooltiptext:  knownBrowsers[i]
            }
        });
    }

    browserMenulist.$elem.on("command", function(e)
                             {
                                storePref(['browser',
                                           this.selectedItem.label,
                                           'string']);
                             });
    page1.addRow(browserMenulist.$elem);
    // END BROWSER PREF
    
    // ADD COLOR SCHEME PREF
    var currentColorScheme = prefs.getString("editor-scheme");
    var schemeService = Cc['@activestate.com/koScintillaSchemeService;1'].getService();
    var schemes = new Array();
    schemeService.getSchemeNames(schemes, new Object());
    schemes = schemes.value;
    var colorSchemeList = require("ko/ui/menulist").create({
        attributes:
        {
            id: "schemelist",
            label:"Choose an editor color scheme",
            width: 200,
            
        }
    });
    for(let i in schemes)
    {
        var $menuitem = colorSchemeList.addMenuitem({
            attributes: {
                label: schemes[i],
                //tooltiptext:  schemes[i]
            }
        });
       
        var s = schemeService.getScheme(schemes[i]);
        $menuitem.css(
            {
                "font-family": s.getCommon("default_fixed", "face"),
                color: s.getCommon("default_fixed", "fore"),
                background: s.getCommon("default_fixed", "back")
            }
        );
        $menuitem._isDark = s.isDarkBackground;

    }
    colorSchemeList.$elem.on("command", function()
                             {
                                storePref(['editor-scheme',
                                           this.selectedItem.label, 'string']);
                             });
    // sort by dark scheme
    colorSchemeList.$elem.children().each(function ()
    {
        if (this._isDark)
        {
            while (this.previousSibling && ! this.previousSibling._isDark) {
                this.parentNode.insertBefore(this, this.previousSibling);
            }
        }
    });
    page1.addRow(colorSchemeList.$elem);
    // END COLOR SCHEME PREFS
    
    // Add set tab width pref
    var tabWidth = prefs.getLong("tabWidth")
    var textboxAttrs =
    {
        label: "Set global with of tabs and indents in spaces.",
        value: tabWidth,
        width: 20,
        tooltiptext: "tab/indent width in spaces",
        
    }
    var tabWidthTextfield = require("ko/ui/textbox").create(
        {attributes: textboxAttrs}
    )
    tabWidthTextfield.$elem.on("keyup", function()
        {
            // check if the input is a number and greater than 0
            if(/^\d+$/.test(this.value) && this.value > 0)
            {
                canFinish = true;
                storePref(["tabWidth", this.value, "long"]);
                storePref(["indentWidth", this.value, "long"]);
                $(this).css("border-style", "none");
                $("#tabWarning").remove();
            }
            else
            {
                // THIS IS NOT WORKING
                try{
                    canFinish = false;
                    log.debug("THis is broken - 1");
                    $("#tabWarning").remove();
                    var $warningMsg = $($.create("hbox",
                        {
                            id:"tabWarning",
                            value: "Input must be a number and greater than 0",
                            text: "Input must be a number and greater than 0"
                        }).toString());
                    $warningMsg.css(
                                    {
                                        "color": "red",
                                        "border-style": "solid"
                                    });
                    $(this).children().append($warningMsg);
                    $(this).css("border-color", "red")
                    log.debug("THis is broken - 2");
                } catch (e){
                    log.exception("Something went wrong: " + e);
                }
            }
        });
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
    // Don't allow pref to be set multiple times
    for(let i in storedPrefs)
    {
        if(storedPrefs[i][0] == prefset[0])
        {
            // replace existing saved prefset with the new set
            storedPrefs.splice(i, 1, prefset);
            log.debug("Storing pref: " + storedPrefs[storedPrefs.length - 1]);
            return;
        }
    }
    storedPrefs.push(prefset);
    log.debug("Storing pref: " + storedPrefs[storedPrefs.length - 1]);
}

/**
 * Apply all the prefs that we've gone through in the wizard to finalize the
 * process
 */
function finished()
{
    log.debug("can finish: " + canFinish);
    if(!canFinish)
    {
        // this doesn't work either...window just closes.
        return false;
    }
    for(let i in storedPrefs)
    {
        // [name, value, type]
        var prefset = storedPrefs[i];
        switch(prefset[2])
        {
            case "bool":
                log.debug("setting pref: " + prefset[0] + " to " + prefset[1])
                prefs.setBoolean(prefset[0], prefset[1]);
                break;
            case "string":
                log.debug("setting pref: " + prefset[0] + " to " + prefset[1])
                prefs.setStringPref(prefset[0], prefset[1]);
                break;
            case "long":
                log.debug("setting pref: " + prefset[0] + " to " + prefset[1])
                prefs.setLong(prefset[0], prefset[1]);
                break;
            default:
                log.warn("Could not set preferences: " + prefset[0] +
                         " with value: " + prefset[1] +
                         " and type: " + prefset[2]);
        }
    }
    
    prefs.setBoolean("wizard.finished", true);
    var wizardComplete = new Event('wizard.complete');
    window.dispatchEvent(wizardComplete);
    
    return true;
}

function ok()
{
    return finished();
}

function cancel()
{
    //var wizardComplete = new Event('wizard.complete');
    window.dispatchEvent(wizardComplete);
    
    return true;
}

