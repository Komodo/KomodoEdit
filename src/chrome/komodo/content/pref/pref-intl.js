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

var log = ko.logging.getLogger("pref-intl");

// Constants and global variables
const {classes: Cc, interfaces: Ci} = Components;
const XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";
var timeSvc = Cc["@activestate.com/koTime;1"]
                .getService(Ci.koITime);

var koEncodingServices = Cc["@activestate.com/koEncodingServices;1"]
                           .getService(Ci.koIEncodingServices);
var gPrefSet;
var langToUse;
var latestLanguage;
var dialog = null;
var defaultDateFormat;

function PrefIntl_OnLoad() {
    log.info("PrefIntl_OnLoad");
    try {
        // set up UI elements
        dialog = {};
        dialog.newlangList = document.getElementById('newlangList');
        dialog.newencodingList = document.getElementById('newencodingList');
        dialog.bomBox = document.getElementById('bomBox');
        dialog.encodingDefault = document.getElementById('encodingDefault');
        dialog.encodingAutoDetect = document.getElementById('encodingAutoDetect');
        dialog.encodingXMLDec = document.getElementById('encodingXMLDec');

        // Must do this before calling .onpageload() because the
        // appropriate menuitems must exist for the 'encodingDefault' pref
        // value to be applied to the UI.
        createDefaultEncodingMenu();

        // register with preferences
        parent.hPrefWindow.onpageload();

        updateNewFilesEncodingSection();
        updateForStartupEncoding();
    } catch(ex) {
        log.exception(ex);
    }
}

function OnPreferencePageInitalize(prefset) {
    log.info("OnPreferencePageInitalize");
    try {
        // set up the prefs
        // the new prefset here is the set of changed prefs; it inherits from
        // the given prefset to pick up the unchanged prefs.
        gPrefSet = Cc["@activestate.com/koPreferenceRoot;1"]
                     .createInstance(Ci.koIPreferenceRoot);
        gPrefSet.inheritFrom = prefset;

        let view = getKoObject('views').manager.currentView;
        if (view)
            langToUse = view.koDoc.language;
        else   // default
            langToUse = "Text";

        // "Date & Time" stuff.
        defaultDateFormat = prefset.getStringPref("defaultDateFormat");
    } catch(ex) {
        log.exception(ex);
    }
}

function OnPreferencePageOK(prefset)  {
    log.info("PrefIntl_OkCallback");
    try {
        if (!setEncoding())  {  // check if encoding is appropriate
            return false;
        }

        // "Date & Time" validation.
        var defaultDateFormat = null;
        var dateFormatWidget = document.getElementById("defaultDateFormat");
        if (dateFormatWidget != null) {
            // If this is the current panel then this OkCallback is called before
            // the OnPreferencePanelUnload so we get the value from the widget.
            defaultDateFormat = dateFormatWidget.value;
        } else {
            // Otherwise (this is NOT the current panel), get the value from the
            // custom object on which the value was set in
            // OnPreferencePanelUnload.
            defaultDateFormat = defaultDateFormat;
        }
        if (!defaultDateFormat) {
            //XXX Would like to check defaultDateFormat.strip() but JavaScript does
            //    not have this method.
            var bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
                .getService(Components.interfaces.nsIStringBundleService)
                .createBundle("chrome://komodo/locale/pref/pref-languages.properties");
            return ignorePrefPageOKFailure(prefset,
                bundle.GetStringFromName("InternationalizationInvalidDateTimeFormat"),
                bundle.GetStringFromName("i18nDateFormatShouldNotBeEmpty"));
        }

        return true;
    } catch (ex) {
        log.exception(ex);
    }
    return false;
}

// Start up & returning to this panel in a session
function OnPreferencePageLoading(prefset) {
    log.info("OnPreferencePageLoading");
    try {
        //XXX Shouldn't I be grabbing the date format from "?
        _setupDateShortcuts();
        setDateFormatExample();
    } catch (ex) {
        log.error(ex);
    }
}

function OnPreferencePageClosing(prefset, ok)  {
    if (ok) {
        prefset.update(gPrefSet);
    }
}

function updateNewFilesEncodingSection() {
    var init_hierarchy = koEncodingServices.encoding_hierarchy;
    var menupopup = ko.widgets.getEncodingPopup(init_hierarchy, true, 'changeNewEncoding(this)');

    // Add default option to the top of the list -> Auto-Detect
    var menuitem = document.createElementNS(XUL_NS, 'menuitem');
    menuitem.setAttribute('label', 'Default Encoding');
    menuitem.setAttribute('data', 'Default Encoding');
    menuitem.setAttribute('oncommand', 'changeNewEncoding(this)');
    menupopup.insertBefore(menuitem, menupopup.childNodes[0]);

    dialog.newencodingList.removeChild(dialog.newencodingList.firstChild);
    dialog.newencodingList.appendChild(menupopup);
    updateMenuListValue(dialog.newencodingList, dialog.newencodingList.firstChild.firstChild);
    changeNewLanguage(null, langToUse);
}

function updateMenuListValue(menulist, item) {
    menulist.setAttribute('label', item.getAttribute('label'));
    menulist.setAttribute('data', item.getAttribute('data'));
}

function doBOM(encodingInfo)  {
    var bom = encodingInfo.byte_order_marker != '';
    if (bom)  {
        dialog.bomBox.removeAttribute('disabled');
        return true;
    }
    else  {
        dialog.bomBox.setAttribute('disabled', 'true');
        return false;
    }
}

function _setSelectedEncoding(elt,encoding) {
    var items = elt.getElementsByTagName("menuitem");
    for (var i=0;i<items.length;i++) {
        var item = items[i];
        //dump("Item value is " + item.getAttribute("value") + ", label is " + item.getAttribute("label") + "\n");
        if (item.getAttribute('data') == encoding) {
            //dump("set menu popup to " + item.getAttribute("label") + "\n");
            elt.setAttribute("value", encoding);
            updateMenuListValue(elt, item);
            return;
        }
    }
}

function _getPrefName(prefName) {
    return 'languages/' + latestLanguage + '/' + prefName;
}

function changeNewLanguage(item, name)  {
    var encoding;
    if (item == null)  {  // startup - first time in
        latestLanguage = name;
        dialog.newlangList.selection = name;
    }
    else  {
        var value = dialog.newlangList.selection;
        latestLanguage = value;
    }

    if (gPrefSet.hasPref(_getPrefName('newEncoding')))  {
        encoding = gPrefSet.getString(_getPrefName('newEncoding'));
    } else  {
        log.warn("Could not retrieve " + latestLanguage +
                 " encoding from preferences, using default.");
        encoding = gPrefSet.getString(_getPrefName('encodingDefault'),
                                      'Default Encoding');
    }

    _setSelectedEncoding(dialog.newencodingList, encoding);

    if (encoding == 'Default Encoding') {
        dialog.bomBox.setAttribute('checked', false);
        dialog.bomBox.setAttribute('disabled', 'true');
    } else {
        var encodingInfo = koEncodingServices.get_encoding_info(encoding);
        if (doBOM(encodingInfo))  {
            var bomPref = gPrefSet.getBoolean(_getPrefName('newBOM'), false);
            dialog.bomBox.setAttribute('checked', bomPref);
        }
    }
}

function changeNewEncoding(item)  {
    updateMenuListValue(dialog.newencodingList, item);
    var newEncoding = item.getAttribute('data');
    gPrefSet.setString(_getPrefName('newEncoding'), newEncoding);
    if (newEncoding == 'Default Encoding') {
        dialog.bomBox.setAttribute('checked', false);
        dialog.bomBox.setAttribute('disabled', 'true');
    } else if (doBOM(koEncodingServices.get_encoding_info(newEncoding)))  {
        var bomPref = gPrefSet.getBoolean(_getPrefName('newBOM'), false);
        dialog.bomBox.setAttribute('checked', bomPref);
    }
}

function changeNewBOM(box)  {
    try {
        gPrefSet.setBoolean(_getPrefName('newBOM'), !!box.checked);
    } catch (e) {
        log.exception(e);
    }
}

// Checks to see if encoding selected is appropriate for the file type
function setEncoding()  {
        var koEncoding = Components.classes["@activestate.com/koEncoding;1"]
                    .createInstance(Components.interfaces.koIEncoding);
        var encoding_name = dialog.newencodingList.getAttribute('data');
        if (encoding_name == 'Default Encoding') {
            encoding_name = dialog.encodingDefault.firstChild.firstChild.getAttribute('data');
        }
        koEncoding.python_encoding_name = encoding_name;
        koEncoding.use_byte_order_marker = (dialog.bomBox.getAttribute('disabled') == 'false'
                                        && dialog.bomBox.getAttribute('checked') == 'true')

        var languageRegistry = Components.classes["@activestate.com/koLanguageRegistryService;1"]
                .getService(Components.interfaces.koILanguageRegistryService);
        var language = languageRegistry.getLanguage(dialog.newlangList.selection);

        var warning = language.getEncodingWarning(koEncoding);
        if (warning) {
            ko.dialogs.alert(warning);
            return false;
        }
        if (warning == "" ||
            getKoObject('dialogs').yesNo(
                warning +
                " Are you sure that you want to change the encoding?",
                "No"
            ) == "Yes"
           ) {
            return true;
        }
        // reset the pref ??
        return false;
}


function createDefaultEncodingMenu()  {
    var init_hierarchy = koEncodingServices.encoding_hierarchy;
    var menupopup = ko.widgets.getEncodingPopup(init_hierarchy, true, 'changeOpenEncoding(this)');
    dialog.encodingDefault.removeChild(dialog.encodingDefault.firstChild);
    dialog.encodingDefault.appendChild(menupopup);
    var encodingDefaultValue = (Components.classes["@activestate.com/koPrefService;1"]
                                .getService(Components.interfaces.koIPrefService)
                                .prefs.getStringPref('encodingDefault'));
    if (!encodingDefaultValue) {
        updateMenuListValue(dialog.encodingDefault,
                            dialog.encodingDefault.firstChild.firstChild);
    } else {
        _setSelectedEncoding(dialog.encodingDefault, encodingDefaultValue);
    }
}

function _getSelectedEncoding(elt,encoding) {
    var items = elt.getElementsByTagName("menuitem");
    for (var i=0;i<items.length;i++) {
        var item = items[i];
        //dump("Item value is " + item.getAttribute("value") + ", label is " + item.getAttribute("label") + "\n");
        if (item.getAttribute('data') == encoding) {
            //dump("set menu popup to " + item.getAttribute("label") + "\n");
            elt.setAttribute("value", encoding);
            return item;
        }
    }
    return null;
}

// Do whatever UI changes are necessary depending on the system encoding.
function updateForStartupEncoding() {
    // Determine if the startup/system encoding is supported by Komodo
    // and adjust UI as appropriate.
    //
    // Note: Komodo init handling will have ensured that if the user's chosen
    //       encoding is not supported that 'defaultEncoding' will be reset to
    //       "utf-8".
    var initSvc = Components.classes["@activestate.com/koInitService;1"].
                  getService(Components.interfaces.koIInitService);
    var encodingSvc = Components.classes["@activestate.com/koEncodingServices;1"].
                      getService(Components.interfaces.koIEncodingServices);
    var startupEncoding = initSvc.getStartupEncoding();
    if (encodingSvc.get_encoding_index(startupEncoding) >= 0) {
        // TODO: Add a new menulist entry to the menu if it's not already there.
    }
}


function changeOpenEncoding(item)  {
    updateMenuListValue(dialog.encodingDefault, item);
}


//---- "Date & Time" groupbox methods

function setDateFormatExample()
{
    log.info("setDateFormatExample");
    try {
        var secsNow = timeSvc.time();
        var timeTupleNow = timeSvc.localtime(secsNow, new Object());
        var format = document.getElementById("defaultDateFormat").value
        var example = timeSvc.strftime(format, timeTupleNow.length, timeTupleNow);
        document.getElementById("dateFormatExample").value = example;
    } catch(ex) {
        log.error("setDateFormatExample error: "+ex);
    }
}


function _insertShortcut(textbox, shortcut, replaceAll /* =false*/)
{
    if (typeof replaceAll == 'undefined') replaceAll = false;
    if (replaceAll) {
        textbox.value = shortcut;
        textbox.select();
    } else {
        var oldValue = textbox.value;
        var selStart = textbox.selectionStart;
        var selEnd = textbox.selectionEnd;

        var newValue = oldValue.slice(0, selStart) + shortcut
                       + oldValue.slice(selEnd, oldValue.length);
        textbox.value = newValue;
        textbox.setSelectionRange(selStart + shortcut.length,
                                  selStart + shortcut.length);
    }
}


// Get the shortcut string from the menuitem widget and append it to
// the current command string.
function insertDateShortcut(shortcutWidget, replaceAll /* =false */)
{
    if (typeof replaceAll == 'undefined') replaceAll = false;
    var shortcut = shortcutWidget.getAttribute("shortcut");
    var textbox = document.getElementById("defaultDateFormat");
    _insertShortcut(textbox, shortcut, replaceAll);
    setDateFormatExample();
}

// Set the labels for menuitems on the date shortcuts menupopup that don't have
// a hardcoded label.
function _setupDateShortcuts()
{
    log.info("_setupDateShortcuts");
    var menupopup = document.getElementById("dateShortcutsPopup");
    var menuitems = menupopup.getElementsByTagName("menuitem");
    var secsNow = timeSvc.time();
    var timeTupleNow = timeSvc.localtime(secsNow, new Object());
    var i, item, shortcut, label;
    for (i = 0; i < menuitems.length; ++i) {
        item = menuitems[i];
        if (!item.hasAttribute("label")) {
            shortcut = item.getAttribute("shortcut");
            label = timeSvc.strftime(shortcut, timeTupleNow.length,
                                     timeTupleNow);
            item.setAttribute("label", label);
        }
    }
}

