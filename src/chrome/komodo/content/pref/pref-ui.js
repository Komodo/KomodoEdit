function PrefUi_OnLoad() {
    
    Components.utils.import("resource://gre/modules/Services.jsm");
    
    var menuList = document.getElementById('koSkin_custom_icons');
    var items    = menuList.querySelectorAll('menuitem');
    
    for (let item of items)
    {
        if (item.getAttribute('value') == '')
        {
            continue;
        }
        
        var file = Services.io.newURI("resource://app/chrome/iconsets/" +
                                      item.getAttribute('value') +
                                      "/chrome.manifest", null,null)
                    .QueryInterface(Components.interfaces.nsIFileURL).file;
        
        if (file.exists())
        {
            item.setAttribute('value', file.path);
        }
        else
        {
            item.parentNode.removeChild(item);
        }
    }
    
    parent.hPrefWindow.onpageload();
}