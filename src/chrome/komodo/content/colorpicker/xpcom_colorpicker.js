/* Copyright (c) 2009 ActiveState
   See the file LICENSE.txt for licensing information. */

/**
 * This is a simple XPCOM wrapper around John Dyers excellent JavaScript
 * color picker:
 * http://johndyer.name/post/2007/09/PhotoShop-like-JavaScript-Color-Picker.aspx
 */

Components.utils.import("resource://gre/modules/XPCOMUtils.jsm");

/***********************************************************
 *              XPCOM class definition                     *
 ***********************************************************/

var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
                .getService(Components.interfaces.nsIStringBundleService)
                .createBundle("chrome://komodo/locale/library.properties");

// Class constructor.
function koColorPicker() {}

// Class definition.
koColorPicker.prototype = {
    
    // properties required for XPCOM registration:
    classDescription: _bundle.GetStringFromName("johnDyersColorPicker.desc"),
    
    classID:          Components.ID("{57dbf673-ce91-4858-93f9-2e47fea3495d}"),
    contractID:       "@activestate.com/koColorPicker;1",
    
    // Category: An array of categories to register this component in.
    _xpcom_categories: [{
  
      // Each object in the array specifies the parameters to pass to
      // nsICategoryManager.addCategoryEntry(). 'true' is passed for both
      // aPersist and aReplace params.
      category: "colorpicker",
  
      // optional, defaults to the object's classDescription
      //entry: "",
  
      // optional, defaults to the object's contractID (unless 'service' is specified)
      //value: "...",
  
      // optional, defaults to false. When set to true, and only if 'value' is
      // not specified, the concatenation of the string "service," and the
      // object's contractID is passed as aValue parameter of addCategoryEntry.
       service: false
    }],

    // QueryInterface implementation, e.g. using the generateQI helper (remove argument if skipped steps above)
    QueryInterface: XPCOMUtils.generateQI([Components.interfaces.koIColorPicker]),

    chromeURL: "chrome://komodo/content/colorpicker/colorpicker.html",

    /**
     * Select a color from the Komodo color picker dialog.
     * 
     * @param hexColor {string} - The initial color.
     */
    pickColor: function(hexColor) {
        return this.pickColorWithPositioning(hexColor, -1, -1);
    },

    pickColorWithPositioning: function(hexColor, screenX, screenY) {
        /**
         * @type {Components.interfaces.koIPreferenceSet}
         */
        var prefs = Components.classes["@activestate.com/koPrefService;1"].
                        getService(Components.interfaces.koIPrefService).prefs;
        var colorMode = 'h';
        if (prefs.hasStringPref("colorpicker.colorMode")) {
            colorMode = prefs.getStringPref("colorpicker.colorMode");
        }

        var args = {
            hexColor: hexColor,
            colorMode: colorMode,
            retval: 0
        };
        args.wrappedJSObject = args;

        var win = Components.classes['@mozilla.org/appshell/window-mediator;1']
                      .getService(Components.interfaces.nsIWindowMediator)
                      .getMostRecentWindow(null);
        var windowFeatures = 'chrome,modal,titlebar,resizable';
        if (screenX >= 0)
            windowFeatures += ",left=" + screenX;
        if (screenY >= 0)
            windowFeatures += ",top=" + screenY;
        win.openDialog(this.chromeURL, 'Color Picker',
                       windowFeatures, args);

        if (args.retval) {
            // Remember the last color mode used, for next time.
            prefs.setStringPref("colorpicker.colorMode", args.colorMode);
            return args.hexColor;
        }
        return null;
    }
};

// XPCOM registration of class.
var components = [koColorPicker];
function NSGetModule(compMgr, fileSpec) {
    return XPCOMUtils.generateModule(components);
}
