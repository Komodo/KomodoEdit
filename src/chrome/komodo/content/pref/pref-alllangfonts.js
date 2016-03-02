(function() {
    
    var require = parent.opener.require;
    var $ = require("ko/dom");
    var ko = require("ko/windows").getMain().ko;
    
    this.init = () =>
    {
        $("#openEditor", window).on("command", () =>
        {
            if (parent.hPrefWindow.deck.childNodes.length > 1)
            {
                var answer = ko.dialogs.yesNoCancel("This will close the preferences window. Do you want to save your preferences?");
                if (answer == "Cancel") 
                    return false;

                if (answer == "Yes" && ! parent.hPrefWindow.onApply())
                    return false;
            }
            
            // Don't wait for openDialog
            setTimeout(function() {
                parent.hPrefWindow.doClose();
            }, 0);
            
            ko.windowManager.openDialog("chrome://komodo/content/dialogs/colorscheme.xul",
                    "Komodo:ColorSchemeEditor",
                    "chrome,dialog,modal,resizable,close,centerscreen"
            );
        });
        parent.hPrefWindow.onpageload();
    }
    
    window.OnLoad = this.init;
    
})();