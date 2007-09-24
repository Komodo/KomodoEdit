/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/* file contains functionality needed from any window that would want
   to open the prefs dialogs. */

function prefs_doGlobalPrefs(panel)  {
    // Handle cancel from prefs window
    var resp = new Object ();
    resp.res = "";
    try {
        ko.windowManager.openOrFocusDialog(
                "chrome://komodo/content/pref/pref.xul",
                'komodo_prefs',
                "chrome,resizable,close=yes",
                panel, resp);
    } catch(ex) {
        ko.main.log.error(ex);
        //log.warn("error opening preferences dialog:"+ex);
        return false;
    }
    if (resp.res != "ok") {
        return false;
    }
    return true;
}
