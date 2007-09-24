/* Copyright (c) 2007 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/**
 * An extension to add dialog-based spellchecking of text parts of files.
 */


function spellcheckerLauncher_run() {
    var obj = {};
    try {
        obj.view = ko.views.manager.currentView;
        obj.ko = ko;
    } catch(ex) {
        alert("Komodo Internal Error: couldn't find the document/view object: " + ex);
        return;
    }
    // let the context-menu go away
    setTimeout(function(win) {
        win.openDialog("chrome://komodospellchecker/content/koSpellCheck.xul",
                          "spellchecker",
                          "chrome,modal,titlebar",
                          obj);
    }, 1, window);
}
