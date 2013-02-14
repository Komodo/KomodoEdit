/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/. */

(function() {
    
    function init()
    {
        if (typeof ko != 'undefined' && ko.less != undefined)
        {
            load();
            return;
        }
        
        var topWindow = _topWindow();
        
        if (topWindow == window)
        {
            // This script should never be in a top window, bail!
            return;
        }
        
        if (topWindow.ko == undefined || topWindow.ko.less == undefined)
        {
            topWindow.addEventListener('ko.less.initialized', init);
            return;
        }

        if (typeof ko === "undefined")
        {
            window.ko = {};
        }
        ko.less = topWindow.ko.less;

        load();
    }
    
    function load()
    {
        ko.less.load(window);
    }
    
    function _topWindow(currentWindow = window)
    {
        var win = currentWindow;
        for(;;) {
            while (win.parent && win.parent !== win)
            {
                win = win.parent;
            }

            // Account for new komodo windows
            if (win.document.documentElement.getAttribute("windowtype") == "Komodo")
            {
                return win;
            }

            if ( ! win.opener || win.opener == win)
            {
               return win.opener;
            }

            win = win.opener;
        }
    }
    
    init();

})();
