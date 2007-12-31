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
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
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

var os = Components.classes["@activestate.com/koOs;1"].getService(Components.interfaces.koIOs);

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

function koPrefWindow( frame_id, prefset /* = null */ )
{
    if (frame_id)
        this.deck = document.getElementById(frame_id);
    else
        this.deck = null;

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
    this.helper = new prefTreeHelper("prefsTree");
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
        this.orig_prefset.addObserver(this);

        // debug
        //cnt=new Object(); ids=new Object();this.prefset.getPrefIds(ids, cnt);
        //dump("Pref IDs using are " + ids.value + "\n");
    },

    observe: function(subject, topic, data) {
        if (typeof(prefLog) != "undefined" && prefLog) {
            prefLog.warn("Original prefset changed while in pref window ("+topic+","+data+"). "+
                         "If you get this message, a pref panel is incorrectly modifying prefs "+
                         "and the modified value will be lost.");
        }
    },
    
    finalizePrefset: function() {
        try {
            this.orig_prefset.removeObserver(this);
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
                if (!contentFrame.contentWindow.OnPreferencePageOK(prefset)) {
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
    _onOK: function () {
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

        this._doClosingHandlers(true);

        if (this.deck != null) {
            // persist which preference panel is currently open
            var selectedId = this.helper.getSelectedItemId();
            Components.classes["@activestate.com/koPrefService;1"]
                  .getService(Components.interfaces.koIPrefService).prefs
                  .setStringPref('defaultSelectedPref', selectedId);
        }
        
        this.setResult('ok');
        return true;
        } catch (e) {
            prefLog.exception(e);
        }
        return false;
    },

    onOK: function () {
        if (this._onOK()) {
            close();
            return true;
        }
        return false;
    },
    
    onCancel: function () {
        try {
            if (!this._doCancelHandlers())
                return false;
            this.finalizePrefset();
            this._doClosingHandlers(false);
    
            // persist which preference panel is currently open
            var selectedId = this.helper.getSelectedItemId();
            Components.classes["@activestate.com/koPrefService;1"]
                  .getService(Components.interfaces.koIPrefService).prefs
                  .setStringPref('defaultSelectedPref', selectedId);
    
            this.setResult('cancel');
            close();
        } catch(e) {
            prefLog.exception(e);
            return false;
        }
        return true;
    },

    setResult: function (res) {
        if (window.arguments && window.arguments[1])
            window.arguments[1].res=res;
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

    _setElementFromPrefValue: function(elt) {
    try {
        // Set a UI element from its preference value(s).
        // Returns the preference value (which may not be the label on the widget,
        // especially for menu lists, radios, etc
        var prefIds = null;
        var prefHere = elt.hasAttribute("prefhere") &&
                       elt.getAttribute('prefhere') == "true";
        if (elt.hasAttribute("prefstring")) {
            prefIds = [elt.getAttribute("prefstring")];
        } else if (elt.hasAttribute("prefstrings")) {
            prefIds = elt.getAttribute("prefstrings").split(",");
        } else {
            prefIds = [elt.id];
        }
        var prefValues = [];
        var i;
        for (i = 0; i < prefIds.length; ++i) {
            prefValues.push(this.getPref(prefIds[i], prefHere));
        }

        var prefattribute, items, item, listitem, widgetValues;
        switch (elt.localName) {
        case "listbox":
            prefattribute = _getPrefAttributeForElement(elt);
            while (elt.firstChild) {
                elt.removeChild(elt.firstChild);
            }
            var dirs = prefValues[0].split(os.pathsep);
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
            items = elt.getElementsByTagName("radio");
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
        prefLog.error("Could not set widget '" + elt.id + "' (pref ids '" +
                      prefIds.join(',') + "') to values '" +
                      prefValues.join(',') + "'");
        throw("Invalid preference");
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
                else
                    value = elt.getAttribute( prefattr );
                //dump("widget '" + elt.id + "set preference val to '" + value + "'\n");
                return value;
            }
        }
        prefLog.error("Could not get preference value from element '" + elt.id + "'");
        throw("Invalid preference");
    } catch (e) {
        prefLog.exception(e);
    }
    return null; // shut-up strict mode.
    },

    hasPrefHere: function (aPrefString) {
        var prefs = this._getCurrentPrefSet();
        return prefs.hasPrefHere(aPrefString);
    },

    getPref: function (aPrefString, prefHere) {
        var prefs = this._getCurrentPrefSet();
        if (prefHere && !prefs.hasPrefHere(aPrefString)) {
            return null;
        }
        var aPrefType = prefs.getPrefType(aPrefString);
        if (aPrefType == null) {
            var msg = "pref.id is UNDEFINED, aPrefString = " + aPrefString;
            prefLog.error(msg);
            throw msg;
        }
        switch ( aPrefType ) {
        case "boolean":
            return prefs.getBooleanPref(aPrefString);
            break;
        case "long":
            return prefs.getLongPref(aPrefString);
            break;
        case "double":
            return prefs.getDoublePref(aPrefString);
            break;
        case "string":
            return prefs.getStringPref(aPrefString);
            break;
        default:
            return prefs.getPref(aPrefString);
            break;
        }
        return null;  // shutup strict mode
    },

    setPref: function ( prefId, value ) {
        var prefs = this._getCurrentPrefSet();
        var prefType = prefs.getPrefType(prefId);
        if (prefType == "boolean") {
            if (typeof(value)=="string")
                value = value == "true" ? true : false;
            prefs.setBooleanPref(prefId, value);
        } else if (prefType == "long") {
            prefs.setLongPref(prefId, value);
        } else if (prefType == "double") {
            prefs.setDoublePref(prefId, value);
        } else if (prefType == "string") {
            prefs.setStringPref(prefId, value);
        } else {
            throw "Unknown preference type ("+prefType+")";
        }
    },

    savePrefs: function () {
        // first, remove our observer at this point so we do not get
        // erroneous messages about prefs getting updated
        if (this.orig_prefset) {
            try {
                this.orig_prefset.removeObserver(this);
            } catch(e) { /* do nothing */ }
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
        var selectedRow = this.helper.getSelectedRow();
        var panelName = selectedRow.firstChild.getAttribute("label");
        if (typeof(this.contentFrames[panelName]) == 'undefined') {
            var XUL_NS="http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";
            this.contentFrame = document.createElementNS(XUL_NS,'iframe');
            this.contentFrames[panelName] = this.contentFrame;
            this.deck.appendChild(this.contentFrame);
            var url = selectedRow.firstChild.getAttribute("url");
            this.contentFrame.setAttribute("src", url);
        } else {
            this.contentFrame = this.contentFrames[panelName];
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
        for (i = 0; i < elements.length; i++) {
            var element = elements[i];
            var prefIds = null;
            if (element.hasAttribute("prefstring")) {
                prefIds = [element.getAttribute("prefstring")];
            } else if (element.hasAttribute("prefstrings")) {
                prefIds = element.getAttribute("prefstrings").split(",");
            } else {
                prefIds = [element.id];
            }

            try {
                var widgetValues;
                if (prefIds.length > 1) {
                    widgetValues = this._getPrefValueFromElement(element).split(',');
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
                    var prefValue = this.getPref(prefIds[j]);
                    if (this.hasPrefHere(prefIds[j]) &&
                        (prefValue == widgetValues[j] ||
                         (widgetValues[j] == "true"  && prefValue === true) ||
                         (widgetValues[j] == "false" && prefValue === false))){
                        // do nothing, the value has not changed
                    } else {
                        //dump("savesinglepageprefs: setting preference ID '" +
                        //     prefIds[j] + "' to value '" +
                        //     widgetValues[j] +"'\n");
                        this.setPref(prefIds[j], widgetValues[j]);
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
        var prefset = this._getCurrentPrefSet();
        // First see if we need the once-only "OnPreferencePageInitalize" function.
        if( this.contentFrame && ('OnPreferencePageInitalize' in this.contentFrame.contentWindow)) { // is there a start function.
            try {
                this.contentFrame.contentWindow.OnPreferencePageInitalize(prefset);
            } catch (e) {
                prefLog.error("Calling 'OnPreferencePageInitalize' function failed: " + e);
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
        // Call the page loading function.
        if( this.contentFrame && ('OnPreferencePageLoading' in this.contentFrame.contentWindow)) { // is there a start function.
            this.contentFrame.contentWindow.OnPreferencePageLoading(prefset);
        }
    },

    closeBranches: function ( aComponentName ) {
        var panelChildren = document.getElementById( "panelChildren" );
        var panelTree = document.getElementById( "prefsTree" );
        for( var i = 0; i < panelChildren.childNodes.length; i++ ) {
            var currentItem = panelChildren.childNodes[i];
            if( currentItem.id != aComponentName && currentItem.id != "appearance" )
                currentItem.removeAttribute( "open" );
        }
        var openItem = document.getElementById( aComponentName );
        panelTree.selectItem( openItem );
    }
};



/* tree support functions

   these functions can be used if trees are coded in xul and you are
   not using a view class like the one above.  Primarily this helps
   in retreiving the selected treerow.

   XXX This certainly could be optimized
   but this is just a quick fix for moving to 1.3
*/
function prefTreeHelper(treeid) {
    this.tree = document.getElementById(treeid);
}
prefTreeHelper.prototype = {
    getTreeEntries: function(treechildren, all_entries) {
        var entries = [];
        for (var i=0;i<treechildren.childNodes.length;i++) {
            var treeitem = treechildren.childNodes[i];
            entries[entries.length] = treeitem.firstChild; // treerow
            if (treeitem.getAttribute('container') == 'true' &&
                (all_entries || treeitem.getAttribute('open') == 'true')) {
                var children = this.getTreeEntries(treeitem.firstChild.nextSibling,all_entries);
                if (children.length > 0)
                    entries = entries.concat(children);
            }
        }
        return entries;
    },
    getVisibleRowByIndex: function(index) {
        this.entries = this.getTreeEntries(this.tree.firstChild.nextSibling,false);
        return this.entries[index];
    },
    getVisibleRowById: function(id) {
        this.entries = this.getTreeEntries(this.tree.firstChild.nextSibling,
                                           false);
        for (var i=0; i < this.entries.length; i++) {
            if (this.entries[i].parentNode.id == id)
                return i - 1;
        }
        return -1;
    },
    getRowIndexById: function(id) {
        this.entries = this.getTreeEntries(this.tree.firstChild.nextSibling,true);
        for (var i=0; i < this.entries.length; i++) {
            if (this.entries[i].parentNode.id == id) return i - 1;
        }
        return -1;
    },
    ensureRowVisible: function(row) {
        if (row.parentNode.parentNode.localName == 'treeitem' &&
            row.parentNode.parentNode.getAttribute('open') != 'true')
        {
            row.parentNode.parentNode.setAttribute('open', 'true');
            //XXX I am not sure that this is correct. I would think the arg
            //    should be "row.parentNode.parentNode". However, we currently
            //    have not prefs panels more than 2 levels deep so it
            //    doesn't really matter.
            this.ensureRowVisible(row.parentNode.parentNode.firstChild);
        }
    },
    selectRowById: function(id) {
        var row = document.getElementById(id);
        if (!row) return;
        this.ensureRowVisible(row);
        var index = this.getVisibleRowById(id);
        this.tree.view.selection.select(index+1);
    },
    /* returns the current selection (treerow element). */
    getSelectedRow: function() {
        return this.getVisibleRowByIndex(this.tree.currentIndex);
    },
    /* returns the id of the treeitem currently selected */
    getSelectedItemId: function() {
        return this.getVisibleRowByIndex(this.tree.currentIndex).parentNode.getAttribute('id');
    },
    /* returns an array of selected items (treerow elements). */
    getSelectedRows: function() {
        var entries = this.getTreeEntries(this.tree.firstChild.nextSibling,false);
        var start = new Object();
        var end = new Object();
        var numRanges = this.tree.view.selection.getRangeCount();
        var selection = [];
        for (var t=0; t<numRanges; t++){
          tree.view.selection.getRangeAt(t,start,end);
          for (var v=start.value; v<=end.value; v++){
            selection[selection.length] = entries[v];
          }
        }
        return selection;
    }
}

