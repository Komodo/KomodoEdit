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
var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
                .getService(Components.interfaces.nsIStringBundleService)
                .createBundle("chrome://komodo/locale/pref/pref-helplang.properties");
                
var log = ko.logging.getLogger("pref-langhelp");

var currentPrefset = null;
var _lang_changes = {};

function _reset(pref) {
    if (currentPrefset.hasPref(pref)) {
        currentPrefset.deletePref(pref);
    }
    if (currentPrefset.hasPref(pref)) {
        document.getElementById(pref).value = currentPrefset.getStringPref(pref);
    } else {
        document.getElementById(pref).value = '';
    }
    if (typeof(_lang_changes[pref]) != 'undefined') {
        delete _lang_changes[pref];
    }
}

function langhelp_OnLoad() {
    try {
    var gMainWindow = ko.windowManager.getMainWindow();
    // get a keybinding and set the text correctly
    var keylabel = gMainWindow.ko.keybindings.manager.command2keylabel('cmd_helpLanguage');
    var text = _bundle.formatStringFromName("SpecifyWhatCommandKeyShouldRun", [keylabel], 1)+" "+_bundle.GetStringFromName("SetToEmptyToUseDefault");
    var node = document.createTextNode(text);
    document.getElementById('language_help_desc').appendChild(node);
    
    keylabel = gMainWindow.ko.keybindings.manager.command2keylabel('cmd_helpLanguageAlternate');
    text = _bundle.formatStringFromName("SpecifyWhatCommandKeyShouldRun", [keylabel], 1);
    node = document.createTextNode(text);
    document.getElementById('language_help_alt_desc').appendChild(node);
    
    parent.initPanel();
    }catch(e) {dump(e+'\n');}
}

function langhelp_updateLanguage() {
    // get the language name
    var language = document.getElementById('languageName').selection;
    var pref = language + 'HelpCommand';
    // update the pref box
    if (typeof(_lang_changes[pref]) != 'undefined') {
        document.getElementById('helpCommand').value = _lang_changes[pref];
    } else if (currentPrefset.hasPref(pref)) {
        document.getElementById('helpCommand').value = currentPrefset.getStringPref(pref);
    } else {
        // try to get from the language service
        var command = '';
        var langRegistrySvc = Components.classes['@activestate.com/koLanguageRegistryService;1'].
                          getService(Components.interfaces.koILanguageRegistryService);
        var languageObj = langRegistrySvc.getLanguage(language);
        if (languageObj.searchURL) {
// #if PLATFORM == "darwin"
            command = "open "+languageObj.searchURL;
// #else
            command = "%(browser) "+languageObj.searchURL;
// #endif
        }
        document.getElementById('helpCommand').value = command;
    }
}

function langhelp_changeLanguage() {
    var pref = document.getElementById('languageName').selection + 'HelpCommand';
    //dump("new help is "+pref+"=["+document.getElementById('helpCommand').value+"]\n");
    _lang_changes[pref] = document.getElementById('helpCommand').value;
}

function langhelp_reset() {
    var pref = document.getElementById('languageName').selection + 'HelpCommand';
    if (currentPrefset.hasPref(pref)) {
        currentPrefset.deletePref(pref);
    }
    if (currentPrefset.hasPref(pref)) {
        document.getElementById('helpCommand').value = currentPrefset.getStringPref(pref);
    } else {
        document.getElementById('helpCommand').value = '';
    }
    if (typeof(_lang_changes[pref]) != 'undefined') {
        delete _lang_changes[pref];
    }
}

function OnPreferencePageInitalize(prefset) {
    log.info("OnPreferencePageInitalize");
    try {
        currentPrefset = prefset;
        langhelp_updateLanguage();
    } catch(ex) {
        log.error(ex);
    }
}

function OnPreferencePageOK(prefset)  {
    log.info("OnPreferencePageOK");
    try {
        // first, get all our stored changes
        for (var pref in _lang_changes) {
            //dump("setting "+pref+" to "+_lang_changes[pref]+"\n");
            prefset.setStringPref(pref, _lang_changes[pref]);
        }
        // now, check if the text box was changed, and enter pressed
        var pref = document.getElementById('languageName').selection + 'HelpCommand';
        var val = document.getElementById('helpCommand').value;
        if (prefset.hasPref(pref)) {
            var orig = prefset.getStringPref(pref);
            if (orig != val) {
                //dump("setting "+pref+" to ["+val+"]\n");
                prefset.setStringPref(pref, val);
            }
        } else {
                //dump("setting 2 "+pref+" to ["+val+"]\n");
            prefset.setStringPref(pref, val);
        }
        
        return true;
    } catch (ex) {
        log.exception(ex);
        return ignorePrefPageOKFailure(prefset,
                                       _bundle.GetStringFromName("SavingLanguageHelpPrefsFailed"),
                                       ex.toString());
    }
}

// Start up & returning to this panel in a session
function OnPreferencePageLoading(prefset) {
    log.info("OnPreferencePageLoading");
    try {
        currentPrefset = prefset;
    } catch (ex) {
        log.error(ex);
    }
}


