/* Copyright (c) 2003-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

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
    var text = "Specify what command __KEY__ should run on the current "+
               "word/selection.  Set to empty to use Default.";
    var keylabel = gMainWindow.gKeybindingMgr.command2keylabel('cmd_helpLanguage');
    text = text.replace('__KEY__', keylabel);
    var node = document.createTextNode(text);
    document.getElementById('language_help_desc').appendChild(node);
    
    text = "Specify what command __KEY__ should run on the current word/selection.";
    keylabel = gMainWindow.gKeybindingMgr.command2keylabel('cmd_helpLanguageAlternate');
    text = text.replace('__KEY__', keylabel);
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
        log.error(ex);
    }
    return false;
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


