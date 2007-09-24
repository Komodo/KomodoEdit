/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

var gPaths, gListbox;

function PrefWeb_OnLoad()
{
    var prefbrowser;
    if (parent.hPrefWindow.prefset.hasStringPref('browser') &&
        parent.hPrefWindow.prefset.getStringPref('browser'))
        prefbrowser = parent.hPrefWindow.prefset.getStringPref('browser');
    else
        prefbrowser = '';

    var koWebbrowser = Components.classes['@activestate.com/koWebbrowser;1'].
                   getService(Components.interfaces.koIWebbrowser);
    gPaths = koWebbrowser.get_possible_browsers(new Object());
    gListbox = document.getElementById('selectedbrowser');

    var found = false;
// #if PLATFORM == "win"
    gListbox.appendItem('System defined default browser','');
// #else
    gListbox.appendItem('Ask when browser is launched the next time', '');
// #endif

    for (var i=0; i< gPaths.length; i++) {
        gListbox.appendItem(gPaths[i],gPaths[i]);
        if (gPaths[i] == prefbrowser) found = true;
    }
    if (!found && prefbrowser)
        gListbox.appendItem(prefbrowser,prefbrowser);

    parent.hPrefWindow.onpageload();
}

function browseForBrowser() {
    var path = ko.filepicker.openExeFile();
    if (path == null) {
        return null;
    }
    path = path.replace('"', '\\"', 'g');
    if (path.indexOf(' ') != -1) {
        path = '\"' + path + '\"';
    }
    var gListbox = document.getElementById("selectedbrowser");
    gListbox.selectedItem = gListbox.appendItem(path,path);
    return null;
}

function configureProxies() {
    window.openDialog("chrome://komodo/content/pref/pref-proxies.xul",
                      "Komodo:ProxyPrefs",
                      "chrome,dialog,modal,resizable,close,centerscreen",
                      null);
}