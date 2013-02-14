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
            window.addEventListener('ko.less.initialized', load);
            return;
        }
        
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
