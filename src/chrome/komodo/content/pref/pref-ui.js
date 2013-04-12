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

            var uri = "resource://app/chrome/" + dir + "/" +
                        item.getAttribute('value') + "/chrome.manifest";
            var file = Services.io.newURI(uri, null,null)
                        .QueryInterface(Ci.nsIFileURL).file;

            if (file.exists())
            {
                item.setAttribute('value', uri);
            }
            else
            {
                item.parentNode.removeChild(item);
            }
        }
    };
    
    // Load Icons
    var iconSelector    = document.getElementById('koSkin_custom_icons');
    var items           = iconSelector.querySelectorAll('menuitem');
    parseItems(items, 'iconsets');

    // Load Skins
    var skinSelector    = document.getElementById('koSkin_custom_skin')
    items               = skinSelector.querySelectorAll('menuitem');
    parseItems(items, 'skins');
    
    /*
     * Update the selected icon set relative to the selected skin
     */
    var updateIconSetSel = function()
    {
        var iconSet = skinSelector.selectedItem.getAttribute('iconset');
        if ( ! iconSet)
        {
            return;
        }

        var iconSetElem = iconSelector.querySelector('menuitem#pref_appearance_iconset_' + iconSet);
        if (iconSetElem)
        {
            iconSelector.selectedItem = iconSetElem;
        }
    };

    // Update the selected iconset when a skin is changed (if required)
    skinSelector.addEventListener('select', updateIconSetSel);

    // Hide the skin selector if there are no skins
    document.getElementById('pref_appearance_skin_hbox').collapsed = (items.length == 0);
    
    // Run default actions (load prefs and their selected state)
    parent.hPrefWindow.onpageload();

    // If gtk detection is true, disable the skin selection
    if (window.navigator.platform.toLowerCase().indexOf("linux") != -1)
    {
        var checkboxDetect  = document.getElementById('koSkin_use_gtk_detection');
        var menuSkin        = document.getElementById('koSkin_custom_skin');
        var menuIcons       = document.getElementById('koSkin_custom_icons');

        var setSkinState = function()
        {
            menuSkin.disabled = checkboxDetect.checked;
            menuIcons.disabled = checkboxDetect.checked;

            // If gtk detection is enabled, detect the current gtk theme
            // and select the relevant komodo skin (if available)
            if (checkboxDetect.checked)
            {
                getKoObject('skin').gtk.getThemeInfo(function(themeInfo)
                {
                    var skinFile = getKoObject('skin').gtk.resolveSkin(themeInfo);
                    var menuItemValue =  "";
                    if (skinFile)
                    {
                        menuItemValue = skinFile;
                    }

                    var menuItem = skinSelector.querySelector('menuitem[value="' + menuItemValue + '"]');
                    if (menuItem)
                    {
                        if (skinSelector.selectedItem == menuItem)
                        {
                            updateIconSetSel();
                        }
                        else
                        {
                            skinSelector.selectedItem = menuItem;
                        }
                    }
                });
            }
        }

        checkboxDetect.addEventListener('click', setSkinState);
        setSkinState();
    }
}
