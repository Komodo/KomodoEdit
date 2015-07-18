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

var bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://komodo/locale/pref/pref-languages.properties");

function getDirectoryFromTextObject(textlikeObject) {
    // textlikeObject has a 'value' property -- could be a menulist or text field
    var currentFileName = textlikeObject.value;
    if (!currentFileName) {
        return null;
    }
    var osPath = Components.classes["@activestate.com/koOsPath;1"].getService(Components.interfaces.koIOsPath);
    var path = osPath.dirname(currentFileName);
    return path && osPath.exists(path) ? path : null;
}

function loadExecutableIntoInterpreterList(availInterpListID) {
    var availInterpList = document.getElementById(availInterpListID);
    var currentPath = getDirectoryFromTextObject(availInterpList);
    var path = ko.filepicker.browseForExeFile(currentPath);
    if (path) {
        availInterpList.selectedItem = availInterpList.appendItem(path, path);
        return true;
    }
    return false;
}

function loadExecutableIntoTextField(fieldId) {
    var field = document.getElementById(fieldId);
    var currentPath = getDirectoryFromTextObject(field);
    var path = ko.filepicker.browseForExeFile(currentPath);
    if (path) {
        field.value = path;
        return true;
    }
    return false;
}

function loadFilePathIntoTextObject(fieldId) {
    var field = document.getElementById(fieldId);
    var path = ko.filepicker.saveFile(null, field.value);
    if (path) {
        field.value = path;
    }
}


function ignorePrefPageOKFailure(prefset, context, message) {
    var title = bundle.GetStringFromName("ErrorWhileSavingPreferences.label");
    var prompt = bundle.GetStringFromName("pressIgnoreOrFix.prompt");
    var text = context + ": \n" + message;
    var fixText = bundle.GetStringFromName("fix.buttonText");
    var ignoreText = bundle.GetStringFromName("ignore.buttonText");
    var buttons = [fixText, ignoreText];
    var response = fixText;
    var res = getKoObject("dialogs").customButtons(prompt,
                                       buttons,
                                       response,
                                       text,
                                       title);
    return res == ignoreText;
}

/**
 * checkInvalidInterpreter
 * @param - {koIPrefSet} prefset
 * @param - {String} interpreterPrefName
 * @param - {String} defaultInterp -- the current value
 * @param - {String} programmingLanguage -- prog lang name
 * @param - {String} languagePrefPageId --
 *          the ID of the language's content frame.  This is usually
 *          <language.lower> + "Item"; this arg is here for the
 *          outliers.
 * @returns - {Boolean} True if defaultInterp
 *                      is not set, or it corresponds to a valid file name
 */
function checkValidInterpreterSetting(prefset,
                                      interpreterPrefName,
                                      programmingLanguage,
                                      languagePrefPageId) {
    if (typeof(languagePrefPageId) == "undefined") {
        languagePrefPageId = programmingLanguage.toLowerCase() + "Item";
    }
    var defaultInterp = prefset.getString(interpreterPrefName, "");
    if (!defaultInterp || defaultInterp == "") {
        return true;
    }
    var koSysUtils = Components.classes["@activestate.com/koSysUtils;1"].
        getService(Components.interfaces.koISysUtils);
    if (koSysUtils.IsFile(defaultInterp)) {
        return true;
    }
    var prompt = bundle.formatStringFromName("noLangInterpreterFound.template",
                                              [programmingLanguage,
                                               defaultInterp], 2);
    var fixText = bundle.GetStringFromName("fix.buttonText");
    var buttons = [[fixText,
                    bundle.GetStringFromName("fix.accessKey"),
                    null],
                   [bundle.GetStringFromName("ignore.buttonText"),
                    bundle.GetStringFromName("ignore.accessKey"),
                    null]];
    var defaultResponse = bundle.GetStringFromName("fix.buttonText");
    var title = bundle.GetStringFromName("interpreterNotFound.caption");
    var res = ko.dialogs.customButtons(prompt,
                                       buttons,
                                       defaultResponse,
                                       null, // text
                                       title);
    if (res != fixText) {
        //XXX: Should we clear it, or leave it alone?  Komodo functions better if it's cleared,
        // but the value might become valid later on.
        // prefset.setStringPref(interpreterPrefName, "");
        return true;
    }
    var mainPrefWindow = parent;
    mainPrefWindow.hPrefWindow.helper.selectRowById(languagePrefPageId);
    mainPrefWindow.hPrefWindow.switchPage();
    document.getElementById(interpreterPrefName).focus();
    return false;
}

function getOwningFileObject() {
    var file;
    var loadContext = parent.prefInvokeType;
    if (loadContext == "project") {
        if (parent.part) {
            file = parent.part.getFile();
        } else {
            file = parent.view.koDoc.file;
        }
    } else {
        file = null;
        // Not this: parent.opener.window.ko.views.manager.currentView.koDoc.file;
    }
    return file;
}       

function getKoObject(name) {
    var ko = parent.opener.ko;
    if (ko[name]) {
        return ko[name];
    }
    return parent.opener.ko.windowManager.getMainWindow().ko[name];
}

function getMainWindow() {
    return parent.opener.ko.windowManager.getMainWindow();
}

function globalPrefs() {
    return Components.classes["@activestate.com/koPrefService;1"].
        getService(Components.interfaces.koIPrefService).prefs;
}
