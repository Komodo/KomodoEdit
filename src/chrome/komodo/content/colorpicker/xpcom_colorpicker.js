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

// Class constructor.
function koColorPicker() {}

// Class definition.
koColorPicker.prototype = {
    
    // properties required for XPCOM registration:
    classDescription: "ColorPicker XPCOM Component",
    
    classID:          Components.ID("{57dbf673-ce91-4858-93f9-2e47fea3495d}"),
    contractID:       "@activestate.com/koColorPicker;1",
    
    // QueryInterface implementation, e.g. using the generateQI helper (remove argument if skipped steps above)
    QueryInterface: XPCOMUtils.generateQI([Components.interfaces.koIColorPicker]),

    chromeURL: "chrome://komodo/content/colorpicker/colorpicker.html",

    /**
     * Select a color from the Komodo color picker dialog.
     * 
     * @param hexColor {string} - The initial color.
     */
    pickColor: function(hexColor) {
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
        win.openDialog(this.chromeURL, 'Color Picker',
                       'chrome,modal,titlebar,resizable', args);

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
