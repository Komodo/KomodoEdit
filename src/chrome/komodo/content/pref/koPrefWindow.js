/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 * 
 * The contents of this file are subject to the Mozilla Public License
 * Version 1.1 (the "License"); you may not use this file except in
 * compliance with the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 * 
 * Software distributed under the License is distributed on an "AS IS"
 * basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
 * License for the specific language governing rights and limitations
 * under the License.
 * 
 * The Original Code is Komodo code.
 * 
 * The Initial Developer of the Original Code is ActiveState Software Inc.
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2011
 * ActiveState Software Inc. All Rights Reserved.
 * 
 * Contributor(s):
 *   ActiveState Software Inc
 * 
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 * 
 * ***** END LICENSE BLOCK ***** */


// Preference pages can implement any of the following functions:
//
// OnPreferencePageOK(prefset)
//      called when the user clicks ok
//
// OnPreferencePageClosing(prefset, ok)
//      ok will be true if the ok button was clicked, false if the dialog is
//      cancelled
//
//      If you need to do complex processing or you have to call on a service
//      that modifies the global prefs, you MUST do it here, or your changes
//      will be lost.  An example of this was bug 48227 where the file associations
//      were modified in the languageRegistryService prior to the prefs being
//      updated from the temp prefset.  That resulted in the inability to
//      change file associations.
// 
// OnPreferencePageCancel(prefset)
//      called when the user clicks cancel
//
// OnPreferencePageSelect(prefset)
//      called when the user switches to the existing page.
//      Currently commented out.  Uncomment the code and remove these two
//      lines once it's needed.
//
// OnPreferencePageInitalize(prefset)
//      called prior to any pref widgets getting initialized
//
// OnPreferencePageLoading(prefset)
//      called after pref widgets getting initialized
//
// pref pages should handle the onload event for the window, and call into
// parent.hPrefWindow.onpageload().  This will do some initialization, then
// call OnPreferencePageInitalize.  After that, it will initialize the
// pref widgets in the page, then call OnPreferencePageLoading().
//
// alternately, simple pref panels may just call parent.initPanel(); in
// the window onload handler. (eg. pref-debugger.xul)

//
// 
// Note on "magic-pref-hookup-to-widget" handling:
//  The prefs magic-hookup-to-widget handling now allows one to specify that
//  multiple prefs are derived from one widget. This is done by specifying a
//  "prefstrings" attribute (instead of the usual "prefstring", singular) on a
//  widget where pref="true". The "prefstrings" attribute should be a
//  comma-separated list (NO SPACES!) of pref ids. Then, the identified pref
//  attribute should be a comma separated list of pref values. For example:
//
//    <menulist pref="true" prefattribute="data"
//              prefstrings="donotask_restore_workspace,donotask_action_restore_workspace">
//         <menupopup>
//             <menuitem data="false,"   label="Ask me what to do"/>
//             <menuitem data="true,Yes" label="Restore last workspace"/>
//             <menuitem data="true,No"  label="Open no files or projects"/>
//         </menupopup>
//    </menulist>
//
//  This functionality was originally added for the "Don't ask me again"
//  feature of the new dialogs in dialogs.js that use two prefs for their data.
//
//  NOTE: This feature disallows the use of commas in widget pref data (only
//  for the case of multiple-prefs-per-widget). If this ever becomes a problem
//  then we can start encoding this differently or using a different separator.
//

// Note for listboxes:
//  <listbox pref="true" ...> corresponds to a pathsep-separated
//  string pref If we want to separate with other things, this code
//  needs to be changed

const _DEBUG = false;

function initPanel ( )
{
    hPrefWindow.onpageload( )
}

var prefLog = ko.logging.getLogger('prefs');

var { classes: Cc, interfaces: Ci } = Components;
var os = Cc["@activestate.com/koOs;1"].getService(Ci.koIOs);

function _getPrefAttributeForElement(elt) {
    var prefattr = elt.getAttribute("prefattribute");
    if (prefattr) // believe it :)
        return prefattr;
    // use a default
    switch (elt.localName) {
        case "menulist":
        case "textbox":
            return "value";
        case "listbox":
            return "label";
        case "radio":
        case "radiogroup":
        case "checkbox":
            return "checked";
        case "listitem":
            if (elt.hasAttribute('type') && elt.getAttribute('type') == 'checkbox') {
                return "checked";
            } // fall through on purpose otherwise
        default:
            prefLog.error("element '" + elt.getAttribute("id") + "' is of unknown type '" + elt.localName + "' and has no 'prefattribute' tag");
    }
    return "value"; // I guess!
}

window.doneLoading = false;

function koPrefWindow( frame_id, prefset /* = null */, usesDeck /* = false */ )
{
    if (frame_id)
        this.deck = document.getElementById(frame_id);
    else
        this.deck = null;
    if (typeof(usesDeck) == "undefined") usesDeck = false;

    this.contentFrames   = {};
    this.contentFrame = null;
    if (this.deck ==  null) {
        this.contentFrame = {
            contentWindow: window,
            contentDocument: document
        };
        this.contentFrames = {
            0: this.contentFrame
        };
    }

    this.prefset           = null;
    this.prefservice      = null;
    this.orig_prefset = null;
    if (usesDeck) {
        this.helper = this.stdHelper = new prefTreeHelper("filteredPrefsTree");
        this.prefDeckSwitched(document.getElementById("pref-deck").selectedIndex);
    } else {
        this.helper = new prefTreeHelper("prefsTree");
    }
    this.onload();
    this.init(prefset);
}

koPrefWindow.prototype =
{
    onload:	function () {
        // we really need a prefset per panel, but will always need a "global".
        try {
            this.prefservice = Components.classes["@activestate.com/koPrefService;1"].
                getService(Components.interfaces.koIPrefService);
        } catch(e) {
            dump("*** Failed to create preference service object\n");
            return;
        }
    },

    init: function (prefset /* = null */) {
        // setup the prefset.  If not specified, we use the global prefs.
        this.save_prefs_service = false;
        if (this.orig_prefset) {
            this.finalizePrefset();
        }
        if (!prefset) {
            prefset = this.prefservice.prefs;
            this.save_prefs_service = true;
        }
        // Clone the prefset, so we can update that on the fly.
        // When OK is pressed, we update the original with our
        // modified preferences.
        this.prefset = prefset.clone();
        this.orig_prefset = prefset;
        this.orig_prefset.prefObserverService.addObserver(this, '' /* all prefs */, true);

        // debug
        //dump("Pref IDs using are " + this.prefset.getPrefIds() + "\n");
    },

    observe: function(subject, topic, data) {
        if (typeof(prefLog) != "undefined" && prefLog && topic.indexOf("prefs_show_advanced") !== 0) {
            prefLog.warn("The '"+topic+"' preference has changed while the pref window was open. "+
                         "If you get this message, a pref panel is incorrectly modifying prefs "+
                         "and the modified value will be lost.");
        }
    },

    setTreeView: function(filteredTreeView) {
        this.filteredTreeView = filteredTreeView;
        this.helper.setTreeView(filteredTreeView);
    },
    
    finalizePrefset: function() {
        try {
            this.orig_prefset.prefObserverService.removeObserver(this, '' /* all prefs */);
        } catch(e) { /* do nothing */ }
        this.prefset = this.orig_prefset;
        this.orig_prefset = null;
    },
    
    _doOKHandlers: function() {
        var frameName, prefset, contentFrame;
        for( frameName in this.contentFrames ) {
            prefset = this._getCurrentPrefSet();
            contentFrame = this.contentFrames[frameName];
            if( contentFrame && ('OnPreferencePageOK' in contentFrame.contentWindow)) { // is there a start function.
                let ok = false;
                try {
                    ok = contentFrame.contentWindow.OnPreferencePageOK(prefset);
                } catch(e) {
                    prefLog.exception(e);
                }
                if (!ok) {
                    prefLog.debug("OK handler for " + frameName + " returned false - not closing dialog");
                    return false;
                }
            }
        }
        return true;
    },

    _doClosingHandlers: function(ok) {
        var frameName, prefset, contentFrame;
        for( frameName in this.contentFrames ) {
            prefset = this._getCurrentPrefSet();
            contentFrame = this.contentFrames[frameName];
            if( contentFrame && ('OnPreferencePageClosing' in contentFrame.contentWindow)) { // is there a start function.
                try {
                    contentFrame.contentWindow.OnPreferencePageClosing(prefset, ok);
                } catch(e) {
                    prefLog.exception(e);
                }
            }
        }
        return true;
    },

    _doCancelHandlers: function() {
        var frameName, prefset, contentFrame;
        for( frameName in this.contentFrames ) {
            prefset = this._getCurrentPrefSet();
            contentFrame = this.contentFrames[frameName];
            if( contentFrame && ('OnPreferencePageCancel' in contentFrame.contentWindow)) { // is there a start function.
                if (!contentFrame.contentWindow.OnPreferencePageCancel(prefset)) {
                    prefLog.debug("Cancel handler for " + frameName + " returned false - not closing dialog");
                    return false;
                }
            }
        }
        return true;
    },
    /**
     * _onOK: if this function is called and it returns OK, the current
     * pref object is no longer usable.
     */
    _onOK: function (close = true) {
        try {
        // Save the prefs to our temp prefset, so the OK handlers see the new values.
        if (!this.savepageprefs()) {
            prefLog.error("Unable to get the prefs from the pref widgets!");
            return false;
        }

        if (!this._doOKHandlers()) {
            prefLog.debug("OK handlers failed!");
            return false;
        }

        this.savePrefs();

        if (close) {
            this._doClosingHandlers(true);
        }

        if (this.deck != null) {
            this._saveCurrentPref();
        }
        
        if (close) {
            this.setResult('ok');
        }

        return true;
        } catch (e) {
            prefLog.exception(e);
        }
        return false;
    },

    doClose: function() {
        close();
    },

    onOK: function () {
        if ( ! this.onApply(true)) {
            return false;
        }

        this.doClose();
        return true;
    },
    
    onApply: function (close = false) {
        if ( ! this._onOK(close)) {
            return false;
        }

        try {
            this.filteredTreeView.doApply();
        } catch(ex) {
            prefLog.exception(ex);
            return false;
        }

        return true;
    },
    
    onCancel: function () {
        try {
            if (!this._doCancelHandlers())
                return false;
            this.finalizePrefset();
            this._doClosingHandlers(false);
    
            this._saveCurrentPref();
            this.setResult('cancel');
            this.doClose();
        } catch(e) {
            prefLog.exception(e);
            return false;
        }
        return true;
    },

    _saveCurrentPref: function() {
        // persist which preference panel is currently open
        try {
            var selectedID = this.helper.getSelectedItemId();
            Components.classes["@activestate.com/koPrefService;1"]
                  .getService(Components.interfaces.koIPrefService).prefs
                  .setStringPref('defaultSelectedPref', selectedID);
        } catch(e) {
            prefLog.exception(e);
        }
    },

    restoreDefaultPref: function() {
        var selectedID = Components.classes["@activestate.com/koPrefService;1"]
                  .getService(Components.interfaces.koIPrefService).prefs
                  .getStringPref('defaultSelectedPref');
        this.helper.selectRowById(selectedID);
    },

    setResult: function (res) {
        if (window.arguments && window.arguments[1])
        {
            if ( ! res)
                delete window.arguments[1].res
            else
                window.arguments[1].res=res;
        }
        return true;
    },

    // might end up with per-page prefsets.
    _getCurrentPrefSet: function() {
        return this.prefset;
    },

    // Get the DOM element that is the parent of the current pref widgets
    // (ie, the object we can enumerate to find the fields.
    _getPrefElementsParent: function(contentFrame) {
        if (typeof(contentFrame) != 'undefined') {
            return contentFrame.contentDocument;
        }
        if (this.contentFrame) {
            return this.contentFrame.contentDocument;
        }
        return document;
    },

    _prefDataFromElement: function(elt) {
        var data = {
            types: [null],
            defaults: [null],
        };
        if (elt.hasAttribute("prefstring")) {
            data.ids = [elt.getAttribute("prefstring")];
        } else if (elt.hasAttribute("prefstrings")) {
            data.ids = elt.getAttribute("prefstrings").split(",");
        } else {
            data.ids = [elt.id];
        }
        if (elt.hasAttribute("preftype")) {
            data.types = [elt.getAttribute("preftype")];
            if (elt.hasAttribute("prefdefault")) {
                data.defaults = [elt.getAttribute("prefdefault")];
            }
        } else if (elt.hasAttribute("preftypes")) {
            data.types = elt.getAttribute("preftypes").split(",");
            if (elt.hasAttribute("prefdefaults")) {
                data.defaults = elt.getAttribute("prefdefaults").split(",");
            }
        }
        while (data.types.length < data.ids.length) {
            data.types.push(null);
        }
        while (data.defaults.length < data.ids.length) {
            data.defaults.push(null);
        }
        return data;
    },

    _setElementFromPrefValue: function(elt) {
    try {
        // Set a UI element from its preference value(s).
        // Returns the preference value (which may not be the label on the widget,
        // especially for menu lists, radios, etc
        var prefHere = elt.hasAttribute("prefhere") &&
                       elt.getAttribute('prefhere') == "true";
        var prefData = this._prefDataFromElement(elt);
        var prefIds = prefData.ids;
        var prefTypes = prefData.types;
        var prefDefaults = prefData.defaults;
        var prefValues = [];
        var i;
        for (i = 0; i < prefIds.length; ++i) {
            prefValues.push(this.getPref(prefIds[i], prefHere, prefTypes[i], prefDefaults[i]));
        }

        var prefattribute, items, item, listitem, widgetValues, prefValue;
        switch (elt.localName) {
        case "listbox":
            prefattribute = _getPrefAttributeForElement(elt);
            while (elt.firstChild) {
                elt.removeChild(elt.firstChild);
            }
            var prefValue = prefValues[0];
            if (prefValue == null) {
                prefValue = "";
            }
            var dirs = prefValue.split(os.pathsep);
            for (i = 0; i < dirs.length; i++) {
                if (dirs[i]) {
                    listitem = document.createElement('listitem');
                    listitem.setAttribute('label', dirs[i]);
                    elt.appendChild(listitem);
                }
            }
            return;
        case "menulist":
            prefattribute = _getPrefAttributeForElement(elt);
            var popup = elt.getElementsByTagName("menupopup")[0];

            items = elt.getElementsByTagName("menuitem");
            //dump("menulist has " + items.length + " items, prefValues are " +
            //     prefValues.join(",") + "\n");
            for (i = 0; i < items.length; i++) {
                item = items[i];
                if (prefIds.length > 1) {
                    widgetValues = item.getAttribute(prefattribute).split(",");
                    if (widgetValues.length != prefIds.length) {
                        var err = "Incorrect number of values in pref data for <"+elt.tagName+"> element associated with pref ids '"+prefIds.join(',')+"'. The number of pref data values must match the number of pref ids: value='"+item.getAttribute(prefattribute)+"'";
                        prefLog.error(err)
                        alert("Internal Error: "+err);
                        continue;
                    }
                } else /* prefIds.length == 1 */ {
                    widgetValues = [item.getAttribute(prefattribute)];
                }
                if (widgetValues.join(',') == prefValues.join(',')) { // just want to compare lists
                    elt.selectedItem = item;
                    elt.setAttribute("value", prefValues.join(',')); //XXX Why this?
                    return;
                }
            }
            break;

        case "radiogroup":
            prefattribute = _getPrefAttributeForElement(elt);
            // bug89184 - deal with xbl too. Currently only needed for PHP invocation
            // prefs, but add more as needed.
            // Also, watch out -- XUL_NS is defined as a global constant when
            // this file is loaded for invocation prefs, but not for std preferences.
            var XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";
            items = elt.getElementsByTagNameNS(XUL_NS, "radio");
            for (i = 0; i < items.length; i++) {
                item = items[i];
                if (prefIds.length > 1) {
                    widgetValues = item.getAttribute(prefattribute).split(",");
                } else /* prefIds.length == 1 */ {
                    widgetValues = [item.getAttribute(prefattribute)];
                }
                if (widgetValues.join(',') == prefValues.join(',')) { // just want to compare lists
                    //dump("pref values are " + prefValues.join(',') +
                    //     " Item value is " + item.getAttribute(prefattribute) +
                    //     ", label is " + item.getAttribute("label") + "\n");
                    item.checked = true;
                    elt.selectedItem = item;
                    return;
                }
            }

        default:
            if (elt.getAttribute("prefwidget") == "true") {
                elt.value = prefValues.join(',');
                return;
            } else {
                prefattribute = _getPrefAttributeForElement(elt);
                // XX - is this needed?
                // seems a shame that textboxes are different?
                //dump("Set prefs '" + prefIds.join(',') + "' to values '" +
                //     prefValues.join(',') + "'\n");
                if (elt.localName == "textbox" && prefattribute == "value") {
                    elt.value = prefValues.join(',');
                } else {
                    elt.setAttribute(prefattribute, prefValues.join(','));
                }
                return;
            }
        }
        if (elt.getAttribute("prefLoadManually") != "true") {
            prefLog.error("Could not set widget '" + elt.id + "' (pref ids '" +
                          prefIds.join(',') + "') to values '" +
                          prefValues.join(',') + "'");
            throw new Error("Invalid preference");
        }
        return;
    } catch (e) {
        prefLog.exception(e);
    }
    },

    _getPrefValueFromElement: function(elt) {
    try {
        // Given a UI widget, get the value for the preference.
        //dump("_getPrefValue for ID " + elt.tagName + "\n");
        var prefattribute, items, i, item;
        switch (elt.localName) {
        case "menulist":
            prefattribute = _getPrefAttributeForElement(elt);
            var popup = elt.getElementsByTagName("menupopup")[0];
            var popup_value = elt.getAttribute("label");

            items = elt.getElementsByTagName("menuitem");
            for (i=0;i<items.length;i++) {
                item = items[i];
                if (item.getAttribute("label") == popup_value) {
                    //dump("preference value for popup is " + item.getAttribute("value") + "\n");
                    return item.getAttribute(prefattribute);
                }
            }
            break;

        case "listbox":
            prefattribute = _getPrefAttributeForElement(elt);
            items = elt.getElementsByTagName("listitem");
            var val = '';
            for (i=0;i<items.length;i++) {
                item = items[i];
                if (val) {
                    val += os.pathsep;
                }
                val += item.getAttribute(prefattribute);
            }
            return val;

        case "radiogroup":
            prefattribute = _getPrefAttributeForElement(elt);
            items = elt.getElementsByTagName("radio");
            if (elt.selectedItem) {
                //dump("radiogroup has " + items.length + " items, selected item is "+elt.selectedItem.getAttribute(prefattribute)+"\n");
                return elt.selectedItem.getAttribute(prefattribute)
            }
            break;

        default:
            if (elt.getAttribute( "prefwidget" )=="true") {
                return elt.value;
            } else {
                var prefattr = _getPrefAttributeForElement(elt);
                var value;

                //XXX is the special handling of textboxes really needed?
                if (elt.localName == "textbox" && prefattr == "value")
                    value = elt.value;
                else if (elt.localName == "checkbox" && prefattr == "checked")
                    value = elt.checked ? "true" : "false";
                else
                    value = elt.getAttribute( prefattr );
                //dump("widget '" + elt.id + "set preference val to '" + value + "'\n");
                return value;
            }
        }
        if (elt.getAttribute("prefLoadManually") !== "true") {
            prefLog.error("Could not get preference value from element '" + elt.id + "'");
            throw new Error("Invalid preference");
        }
    } catch (e) {
        prefLog.exception(e);
    }
    return null;
    },

    hasPrefHere: function (aPrefString) {
        var prefs = this._getCurrentPrefSet();
        return prefs.hasPrefHere(aPrefString);
    },

    getDefaultValue: function(prefType, prefDefault) {
        switch (prefType) {
            case "boolean":
                return prefDefault == "false" ? false : true;
            case "long":
                return parseInt(prefDefault, 10);
            case "double":
                return parseFloat(prefDefault);
            case "string":
                return prefDefault;
        }
        return null;
    },

    getPref: function (aPrefString, prefHere /* =false */, prefType /* =null */,
                       prefDefault /* =null */) {
        if (typeof(prefHere) == "undefined" || prefHere == null) prefHere = false;
        if (typeof(prefType) == "undefined") prefType = null;
        if (typeof(prefDefault) == "undefined") prefDefault = null;
        
        var prefs = this._getCurrentPrefSet();
        if (prefHere && !prefs.hasPrefHere(aPrefString)) {
            return null;
        }
        if (!prefDefault && !prefs.hasPref(aPrefString)) {
            return null;
        }
        var aPrefType = prefType || prefs.getPrefType(aPrefString);
        if (aPrefType == null) {
            var msg = "pref.id is UNDEFINED, aPrefString = " + aPrefString;
            prefLog.error(msg);
            throw new Error(msg);
        }
        switch ( aPrefType ) {
        case "boolean":
            if (prefDefault)
                return prefs.getBoolean(aPrefString, this.getDefaultValue(aPrefType, prefDefault));
            return prefs.getBooleanPref(aPrefString);
        case "long":
            if (prefDefault)
                return prefs.getLong(aPrefString, this.getDefaultValue(aPrefType, prefDefault));
            return prefs.getLongPref(aPrefString);
        case "double":
            if (prefDefault)
                return prefs.getDouble(aPrefString, this.getDefaultValue(aPrefType, prefDefault));
            return prefs.getDoublePref(aPrefString);
        case "string":
            if (prefDefault)
                return prefs.getString(aPrefString, this.getDefaultValue(aPrefType, prefDefault));
            return prefs.getStringPref(aPrefString);
        default:
            return prefs.getPref(aPrefString);
        }
        return null;  // shutup strict mode
    },

    setPref: function (prefId, value, prefType /* = null */) {
        if (typeof(prefType) == "undefined") prefType = null;
        var prefs = this._getCurrentPrefSet();
        var actualPrefType = prefType || prefs.getPrefType(prefId);
        if (actualPrefType == "boolean") {
            if (typeof(value)=="string")
                value = value == "true" ? true : false;
            prefs.setBooleanPref(prefId, value);
        } else if (actualPrefType == "long") {
            prefs.setLongPref(prefId, value);
        } else if (actualPrefType == "double") {
            prefs.setDoublePref(prefId, value);
        } else if (actualPrefType == "string") {
            prefs.setStringPref(prefId, value);
        } else {
            throw new Error("Unknown preference type ("+actualPrefType+")");
        }
    },

    savePrefs: function () {
        // first, remove our observer at this point so we do not get
        // erroneous messages about prefs getting updated
        if (this.orig_prefset) {
            try {
                this.orig_prefset.prefObserverService.removeObserver(this, '' /* all prefs */);
            } catch(e) { /* do nothing */ }
            let ids = {};

            /**
             * Check if the newly-set preferences are the same as old prefs.
             * @param oldset {koIPreferenceSet} The old pref set
             * @param newset {koIPreferenceSet} The new pref set
             * @param id {String} The sub-pref to check.
             * @returns {Boolean} True if the two sub-prefs are equal.
             */
            let _prefsEqual = function(oldset, newset, id) {
                let type = newset.getPrefType(id);
                if (!type) {
                    return false; // no need to check for non-existing prefs
                }
                if (oldset.getPrefType(id) != type) {
                    return false; // Isn't there in the old prefs / different type
                }
                if (type == "object") {
                    let oldPref = oldset.getPref(id);
                    let newPref = newset.getPref(id);
                    if (oldPref instanceof Ci.koIPreferenceSet &&
                        newPref instanceof Ci.koIPreferenceSet)
                    {
                        let children = newPref.getPrefIds();
                        for (let child of children) {
                            if (!_prefsEqual(oldPref, newPref, child)) {
                                return false;
                            }
                        }
                    } else if (oldPref instanceof Ci.koIOrderedPreference &&
                               newPref instanceof Ci.koIOrderedPreference)
                    {
                        if (oldPref.length != newPref.length) {
                            return false; // Different length
                        }
                        for (let i=0; i < newPref.length; i++) {
                            if (!_prefsEqual(oldPref, newPref, i)) {
                                return false;
                            }
                        }
                    } else {
                        // Reaching here means we failed to have type-specific logic
                        let path = [];
                        try {
                            for (let parent = oldPref; parent; parent = parent.parent) {
                                path.push(parent.id);
                            }
                        } catch (ex) {
                            /* ignore - shouldn't throw, nothing we can do */
                        }
                        prefLog.warn("Can't deal with preference object of types " +
                                     String(oldPref) + " / " + String(newPref) +
                                     " with id " + (path.reverse().join("::") || id));
                        return false; // Can't deal with this pref type?
                    }
                } else {
                    let func = "get" + type.replace(/^./, function(c) c.toUpperCase()) + "Pref";
                    let oldVal = oldset[func](id);
                    let newVal = newset[func](id);
                    if (oldVal != newVal) {
                        return false;
                    }
                }
                return true;
            }

            ids = this.prefset.getPrefIds();
            try {
                for (let id of ids) {
                    if (_prefsEqual(this.orig_prefset, this.prefset, id)) {
                        this.prefset.deletePref(id);
                    }
                }
            } catch(e) {
                prefLog.exception(e, "Failed to trim unchanged prefs, may have unncessary values");
            }
            this.orig_prefset.update(this.prefset);
        }
        if (this.save_prefs_service) {
            this.prefservice.saveState();
        }
        // now reset our current prefset to the original
        this.prefset = this.orig_prefset;
        this.orig_prefset = null;
    },

    switchPage: function () {
        try {
        var url = this.helper.getSelectedCellValue("url");
        if (!url) {
            return;
        }

        var panelName = url;
        if (!(panelName in this.contentFrames)) {
            var XUL_NS="http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";
            this.contentFrame = document.createElementNS(XUL_NS,'iframe');
            this.contentFrames[panelName] = this.contentFrame;
            this.deck.appendChild(this.contentFrame);

            this.contentFrame.addEventListener("load", function() {
                var showAdvanced = this.prefset.getBoolean("prefs_show_advanced", false);
                var docElem = this.contentFrame.contentWindow.document.documentElement;
                docElem.classList.add("pref-window");
                if (showAdvanced) docElem.classList.add("show-advanced");
            }.bind(this), true);
            
            var detail = this.contentFrame.contentWindow;
            var loadEvent = function() {
                var event = new CustomEvent("pref-frame-load",
                {
                    bubbles: false,
                    cancelable: false,
                    detail: detail
                });
                var _window = parent.opener.ko.windowManager.getMainWindow();
                _window.dispatchEvent(event);
            }
            this.contentFrame.addEventListener("load", loadEvent, true);

            this.contentFrame.setAttribute("src", url);
        } else {
            this.contentFrame = this.contentFrames[panelName];
            // if ('OnPreferencePageSelect' in this.contentFrame.contentWindow) {
            //     var prefset = this._getCurrentPrefSet();
            //     try {
            //         this.contentFrame.contentWindow.OnPreferencePageSelect(prefset);
            //     } catch(e) {
            //         prefLog.exception(e);
            //     }
            // }
        }
        this.deck.selectedPanel = this.contentFrame;

        // update the help button
        try {
            canHelp();
        } catch(e) { /* ignore */ }

        // Page OnLoad scripts fire, which end up calling initPage()
        // (which should die - may as well just auto-trigger.)
        } catch(e) {
            prefLog.exception(e);
        }
    },

    prefDeckSwitched: function(selectedIndex) {
        this.helper = (selectedIndex === 0 ? null : this.stdHelper);
    },

    // return the widget on the current page with the pref ID, or null.
    findElementWithPreferenceId: function(prefId) {
        var elements = this._getPrefElementsParent().getElementsByAttribute("pref", "true");
        for (var i = 0; i < elements.length; i++) {
            var element = elements[i];
            var widgetPrefId = element.hasAttribute("prefstring") ? element.getAttribute("prefstring") : element.id;
            if (prefId == widgetPrefId)
                return element;
        }
        return null;
    },

    _doSavePrefElements: function (elements) {
        var i, j;
        var rc = true;
        var prefs = this._getCurrentPrefSet();
        for (i = 0; i < elements.length; i++) {
            var element = elements[i];
            var prefData = this._prefDataFromElement(element);
            var prefIds = prefData.ids;
            var prefTypes = prefData.types;
            var prefDefaults = prefData.defaults;

            try {
                var widgetValues;
                if (prefIds.length > 1) {
                    widgetValues = this._getPrefValueFromElement(element).split(',');
                    if (widgetValues === null) {
                        // Only way this can happen is if prefLoadManually is set?
                        continue;
                    }
                    if (widgetValues.length != prefIds.length) {
                        var err = "Incorrect number of values in pref data for <"+element.tagName+"> element associated with pref ids '"+prefIds.join(',')+"'. The number of pref data values must match the number of pref id: value='"+this._getPrefValueFromElement(element)+"'";
                        prefLog.error(err)
                        alert("Internal Error: "+err);
                        continue;
                    }
                } else /* prefIds.length == 1 */ {
                    widgetValues = [this._getPrefValueFromElement(element)];
                }

                for (j = 0; j < prefIds.length; j++) {
                    var prefValue = this.getPref(prefIds[j], null, prefTypes[j], prefDefaults[j]);
                    if (prefDefaults[j] !== null &&
                        widgetValues[j] == prefDefaults[j] &&
                        !prefs.hasPrefHere(prefIds[j])) {
                        // It's the default value.
                        continue;
                    } else if (this.hasPrefHere(prefIds[j]) &&
                        (prefValue == widgetValues[j] ||
                         (widgetValues[j] == "true"  && prefValue === true) ||
                         (widgetValues[j] == "false" && prefValue === false))){
                        // do nothing, the value has not changed
                    } else {
                        //dump("savesinglepageprefs: setting preference ID '" +
                        //     prefIds[j] + "' to value '" +
                        //     widgetValues[j] +"'\n");
                        this.setPref(prefIds[j], widgetValues[j], prefTypes[j]);
                    }
                }
            } catch (e) {
                prefLog.error("Could not save prefs '" + prefIds.join(',') +
                              "' to values '" + widgetValues.join(',') + "': " +
                              e + "\n");
                rc = false; // but keep updating what prefs we can.
            }
        }
        return rc;
    },

    savepageprefs: function() {
        var frameName, contentFrame;
        for( frameName in this.contentFrames ) {
            contentFrame = this.contentFrames[frameName];
            if (!this.savesinglepageprefs(contentFrame)) {
                return false;
            }
        }
        return true;
    },
    
    savesinglepageprefs: function (contentFrame) {
        var parentDoc = this._getPrefElementsParent(contentFrame);
        var elements = parentDoc.getElementsByAttribute( "pref", "true" );
        if (!this._doSavePrefElements(elements)) {
            return false;
        }
        var prefWidgets = parentDoc.getElementsByAttribute( "prefwidgetauto", "true" );
        for( var i = 0; i < prefWidgets.length; i++ ) {
            var anodes = parentDoc.getAnonymousNodes(prefWidgets[i]);
            if (!anodes) {
                continue;
            }
            for (var ai = 0; ai < anodes.length; ai++) {
                if (anodes[ai].getAttribute('pref')) {
                    if (!this._doSavePrefElements([anodes[ai]])) return false;
                } else {
                    var pels = anodes[ai].getElementsByAttribute( "pref", "true" );
                    if (pels)
                        if (!this._doSavePrefElements(pels)) return false;
                }
            }
        }
        // look for pref-widgets and save the prefs
        prefWidgets = parentDoc.getElementsByAttribute( "prefwidget", "true" );
        for( i = 0; i < prefWidgets.length; i++ ) {
            var widget = prefWidgets[i];
            //dump("calling saveprefs for "+widget.getAttribute("prefstring")+"\n");
            if (typeof(widget.saveprefs) != 'undefined')
                widget.saveprefs(this);
        }
        return true;
    },

    onpageload: function ( ) {
        try {
            var observerSvc = Cc["@mozilla.org/observer-service;1"].
                        getService(Ci.nsIObserverService);
            observerSvc.notifyObservers(null, 'pref_page_loaded', this.contentFrame.contentWindow.location.href);
        } catch(e) {
            // Raises exception if no observers are registered. Just ignore that.
        }
        
        var prefset = this._getCurrentPrefSet();
        // First see if we need the once-only "OnPreferencePageInitalize" function.
        if( this.contentFrame && ('OnPreferencePageInitalize' in this.contentFrame.contentWindow)) { // is there a start function.
            try {
                this.contentFrame.contentWindow.OnPreferencePageInitalize(prefset);
            } catch (e) {
                prefLog.exception("Calling 'OnPreferencePageInitalize' function failed: " + e);
            }
        }

        var parentDoc = this._getPrefElementsParent(this.contentFrame);
        // look for pref-widgets and initialize them
        var prefWidgets = parentDoc.getElementsByAttribute( "prefwidget", "true" );
        for( var i = 0; i < prefWidgets.length; i++ ) {
            var widget = prefWidgets[i];
            //dump("calling onpageload for "+widget.getAttribute("prefstring")+"\n");
            widget.onpageload(this);
        }

        // Setup all our widget values.
        var prefElements = parentDoc.getElementsByAttribute( "pref", "true" );
        //dump("page load loading " + prefElements.length + " items\n");
        for( i = 0; i < prefElements.length; i++ ) {
            var element = prefElements[i];
            this._setElementFromPrefValue(element);
        }

        prefWidgets = parentDoc.getElementsByAttribute( "prefwidgetauto", "true" );
        for( i = 0; i < prefWidgets.length; i++ ) {
            if (typeof(prefWidgets[i].onpageload) != 'undefined') {
                try {
                    prefWidgets[i].onpageload(this);
                } catch (e) {
                    prefLog.exception(e);
                }
            }
            var anodes = parentDoc.getAnonymousNodes(prefWidgets[i]);
            if (anodes) {
                for (var ai = 0; ai < anodes.length; ai++) {
                    if (anodes[ai].getAttribute('pref')) {
                        this._setElementFromPrefValue(anodes[ai]);
                    } else {
                        var pels = anodes[ai].getElementsByAttribute( "pref", "true" );
                        for( i = 0; i < pels.length; i++ ) {
                            element = pels[i];
                            this._setElementFromPrefValue(element);
                        }
                    }
                }
            }
        }
        this._handleLoadContextElements(parentDoc);
        // Call the page loading function.
        if( this.contentFrame && ('OnPreferencePageLoading' in this.contentFrame.contentWindow)) { // is there a start function.
            this.contentFrame.contentWindow.OnPreferencePageLoading(prefset);
        }
    },

    _handleLoadContextElements: function(parentDoc) {
        var i, j, node, nodes = parentDoc.getElementsByClassName("load-context-check");
        var loadContext = parent.prefInvokeType;
        // Set up for an XOR test.
        // If a show-test matches, it will be xor'd with 0 => 1
        // If a hide-test matches, it will be xor'd with 1 => 0
        // etc.
        var attrMatch, attr, hiding, attrTable = [
            ["hideIfLoadContext", 1],
            ["showUnlessLoadContext", 1],
            ["hideUnlessLoadContext", 0],
            ["showIfLoadContext", 0]];
        for (i = 0; i < nodes.length; i++) {
            node = nodes[i];
            for (j = 0; j < attrTable.length; j++) {
                [attr, hiding] = attrTable[j];
                if (node.hasAttribute(attr)) {
                    var doesntMatch = node.getAttribute(attr).split(/\s+/).indexOf(loadContext) === -1 ? 1 : 0;
                    var collapsed = doesntMatch ^ hiding ? "true" : "false";
                    node.setAttribute("collapsed", collapsed);
                    break;
                }
            }
        }
    },

    toggleTreeItems: function(treeView, colId) {
        try {
            var treeViewSelection = treeView.selection;
            var numSelections = treeViewSelection.getRangeCount();
            if (!numSelections) {
                return false;
            }
            var row_indices = [];
            var startRangeObj = {}, endRangeObj = {};
            for (var i = 0; i < numSelections; i++) {
                treeViewSelection.getRangeAt(i, startRangeObj, endRangeObj);
                for (var j = startRangeObj.value; j <= endRangeObj.value; j++) {
                    if (j == -1) {
                        // treeViewSelection.getRangeAt was given invalid input
                        // Not sure how this could happen, but catch it and continue.
                        break;
                    }
                    row_indices.push(j);
                }
            }
            var cs = {colId:1}; // unused arg some tree view implementations want
            // Now determine whether we're toggling down or setting all to true.
            // getCellValue and setCellValue uses strings "true" and "false"
            // to manage the checked state.
            var initState = true;
            var lim = row_indices.length;
            for (var i = 0; initState && i < lim; i++) {
                initState = (initState
                             && (treeView.getCellValue(row_indices[i], cs)
                                 == "true"));
            }
            var targetState = initState ? "false" : "true";
            for (var i = 0; i < lim; i++) {
                treeView.setCellValue(row_indices[i], cs, targetState);
            }
            return false;
        } catch(ex) {
            prefLog.exception(ex);
        }
        return true;
    },

    __END__: null
};

function prefTreeHelper(treeid) {
    this.tree = document.getElementById(treeid);
}
prefTreeHelper.prototype = {
    setTreeView: function(filteredTreeView) {
        this.filteredTreeView = filteredTreeView;
    },
    selectRowById: function(id) {
        var index = this.filteredTreeView.getIndexById(id);
        if (index == -1) {
            prefLog.debug("Can't find pref id '" + id + "'\n");
            index = this.filteredTreeView.findChild(id);
            if (index == -1) {
                prefLog.debug("Still can't find id '" + id + "' after burrowing");
                return;
            }
        }
        this.filteredTreeView.tree.ensureRowIsVisible(index);
        this.filteredTreeView.selection.select(index);
    },
    /* returns the id of the treeitem currently selected */
    getSelectedItemId: function() {
        return this.getSelectedCellValue("id");
    },
    getSelectedCellValue: function(columnName) {
        var index =  this.filteredTreeView.selection.currentIndex;
        if (index == -1) {
            prefLog.debug("No selected item for column " + columnName);
            return null;
        }
        return this.filteredTreeView.getCellValue(index, {id:columnName});
    }
};
