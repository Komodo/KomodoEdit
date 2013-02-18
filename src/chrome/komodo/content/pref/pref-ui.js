function PrefUi_OnLoad() {
    
    const {interfaces: Ci} = Components;
    Components.utils.import("resource://gre/modules/Services.jsm");

    var parseItems = function(items, dir)
    {
        for (let item of items)
        {
            let value = item.getAttribute('value');
            if (value == '' ||
                value.match(/^$|\/|\\/)) // skip full / empty paths
            {
                continue;
            }

            var file = Services.io.newURI("resource://app/chrome/" + dir + "/" +
                                          item.getAttribute('value') +
                                          "/chrome.manifest", null,null)
                        .QueryInterface(Ci.nsIFileURL).file;

            if (file.exists())
            {
                item.setAttribute('value', file.path);
            }
            else
            {
                item.parentNode.removeChild(item);
            }
        }
    };
    
    // Load Icons
    var items = document.querySelectorAll('#koSkin_custom_icons menuitem');
    parseItems(items, 'iconsets');

    // Load Skins
    items = document.getElementById('koSkin_custom_skin')
                            .querySelectorAll('menuitem');
    parseItems(items, 'skins');
    
    // Hide the skin selector if there are no skins
    document.getElementById('pref_appearance_skin_hbox').collapsed = (items.length == 0);
    
    // Run default actions (load prefs and their selected state)
    parent.hPrefWindow.onpageload();

    // If gtk detection is true, disable the skin selection
    if (window.navigator.platform.toLowerCase().indexOf("linux") != -1)
    {
        var checkboxDetect  = document.getElementById('koSkin_use_gtk_detection');
        var menuSkin        = document.getElementById('koSkin_custom_skin');

        var setSkinState = function()
        {
            menuSkin.disabled = checkboxDetect.checked;
        }

        checkboxDetect.addEventListener('click', setSkinState);
        setSkinState();
    }
}
