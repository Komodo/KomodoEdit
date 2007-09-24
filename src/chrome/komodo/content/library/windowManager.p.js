/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

if (typeof(ko) == 'undefined') {
    var ko = {};
}
ko.windowManager = {
    fixupOpenDialogArgs: function(inargs) {
// #if PLATFORM == "darwin"
        // fix features
        if (inargs.length < 2 || !inargs[2]) {
            inargs[2] = "chrome,dialog=no";
        } else if (inargs[2].indexOf("dialog") < 0) {
            inargs[2] = "dialog=no,"+inargs[2];
        }
        var args = [];
        for ( var i=0; i < inargs.length; i++ )
            args[i]=inargs[i];
        return args;
// #else
        return inargs;
// #endif
    },
    /**
     * Open a window if no windows of windowType exist. Otherwise, bring
     * the window of windowType to the front. Parameters for this function
     * are identical to window.openDialog()
     *
     * @param <String> chromeURL
     * @param <String> windowType
     * @param <String> options
     * @param <*> extra arguments for dialog
     * @return <Window>
     */
    openOrFocusDialog: function openDialogUniqueInstance(chromeURI, windowType) {
        var wm = Components.classes["@mozilla.org/appshell/window-mediator;1"]
                            .getService(Components.interfaces.nsIWindowMediator);
        var existingWindow = wm.getMostRecentWindow(windowType);
        if (existingWindow) {
            existingWindow.focus();
            return existingWindow;
        }
        var newArgs = new Array();
        for (var i = 0; i < arguments.length; i++) {
          if (i == 1) {
            newArgs[i] = '_blank';
          } else {
            newArgs[i] = arguments[i];
          }
        }
        return window.openDialog.apply(window, this.fixupOpenDialogArgs(newArgs));
    },
    /**
     * return a reference to the main Komodo window
     *
     * @return <Window>
     */
    getMainWindow: function windowManager_getMainWindow() {
        var wm = Components.classes["@mozilla.org/appshell/window-mediator;1"]
                        .getService(Components.interfaces.nsIWindowMediator);
        return wm.getMostRecentWindow('Komodo');
    },
    /**
     * close all open windows, return true if successful.  The normal
     * goQuitApplication function in toolkit does this, but we want to
     * prevent quitting if one of the dialogs prevents shutdown by not
     * closing.
     *
     * @return <Boolean>
     */
    closeAll: function windowManager_closeAll() {
        var wm = Components.classes["@mozilla.org/appshell/window-mediator;1"]
                            .getService(Components.interfaces.nsIWindowMediator);
    
        // Check for other OPEN windows and close if there
        // This is expandable - just add your windowtype to the array
        try {
            var openWindows = wm.getEnumerator(null);
            do {
                var openWindow = openWindows.getNext();
                if (openWindow && openWindow != window) {
                    openWindow.close();
                    if (!openWindow.closed) {
                        return false;
                    }
                }
            } while (openWindows.hasMoreElements());
        } catch(e) {
            log.exception(e);
        }
        return true;
    }
};
/* handle shutdown requests, check if the namespace exists, if it does
   we are in the main komodo window, so register our shutdown callbacks */
if (typeof(ko.main) != 'undefined') {
    ko.main.addCanQuitHandler(ko.windowManager.closeAll);
    ko.main.addUnloadHandler(ko.windowManager.closeAll);
}

// backwards compatibility APIs
var openWindowUniqueInstance = ko.windowManager.openOrFocusDialog;
var openWindowMultipleInstance = window.openDialog;
function windowManager_getMainWindow() { return ko.windowManager.getMainWindow(); }



