/* Copyright (c) 2003-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */


function PrefNewFiles_OnLoad() {
    if (parent.part) {
        var el = document.getElementById("template-prefs");
        el.parentNode.removeChild(el);
    }
    parent.hPrefWindow.onpageload();
}

function OnPreferencePageLoading(prefset) {
    var newLang = prefset.getStringPref("fileDefaultNew");
    document.getElementById("fileDefaultNew").selection = newLang;
}

function OnPreferencePageOK(prefset) {
    prefset.setStringPref("fileDefaultNew",
                          document.getElementById("fileDefaultNew").selection);
    return true;
}

var _resetMRU = false;
function OnPreferencePageClosing(prefset, ok) {
    if (ok && _resetMRU)
        ko.mru.reset("mruTemplateList");
}

function PrefNewFiles_ClearTemplateMRU() {
    var answer = ko.dialogs.yesNo("Are you sure you would like to clear the "+
                              "list of recently used templates?");
    if (answer == "Yes") {
        _resetMRU = true;
    }
}
